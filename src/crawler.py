from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Final, cast

from bs4 import BeautifulSoup, ResultSet
from bs4.element import Tag
from requests import Response, Session


@dataclass
class UserIdentity:
    id: str
    display_name: str
    username: str


@dataclass
class CarStats:
    races: int
    dqs: int
    avg_wpm: float
    avg_acc: float
    top_wpm: float
    top_acc: float
    perf_acc: int


@dataclass
class Car:
    name: str
    image_url: str


@dataclass
class Quest:
    name: str


@dataclass
class UserQuestProgress:
    quest: Quest
    progress: int


@dataclass
class UserQuests:
    user_id: str
    display_name: str
    quest_progress: list[UserQuestProgress]


@dataclass
class UserStatOverview:
    lifetime_races: int
    longest_session: int
    top_wpm: float
    current_wpm: float
    perfect_races: int
    current_acc: float


@dataclass
class UserStats:
    user_id: str
    display_name: str
    overview: UserStatOverview
    # Add more stats here!


@dataclass
class Garage:
    user_id: str
    display_name: str
    cars: list[Car]
    selected_car: Car
    selected_stats: CarStats


@dataclass
class Team:
    name: str
    tag: str
    leader: UserIdentity
    agents: list[UserIdentity]
    members: list[UserIdentity]


@dataclass
class ShopOffer:
    name: str
    price: int
    image_url: str


@dataclass
class Shop:
    seasonal_offers: list[ShopOffer]
    alices_deals: list[ShopOffer]


class Crawler:
    KlaviaUrl: Final[str] = "https://klavia.io"
    SignInUrl: Final[str] = KlaviaUrl + "/racers/sign_in"
    RacerUrl: Final[str] = KlaviaUrl + "/racers/{user_id}"
    GarageUrl: Final[str] = RacerUrl + "/garage"
    GarageCarsUrl: Final[str] = RacerUrl + "/cars"
    CarInstanceUrl: Final[str] = KlaviaUrl + "/cars/{car_id}"
    StatsUrl: Final[str] = RacerUrl + "/stats"
    QuestsUrl: Final[str] = RacerUrl + "/quests"
    LeaderboardsUrl: Final[str] = KlaviaUrl + "/leaderboards"
    TextsUrl: Final[str] = LeaderboardsUrl + "/texts"
    LeaderboardsCarsUrl: Final[str] = LeaderboardsUrl + "/cars"
    SearchRacerUrl: Final[str] = RacerUrl.format(user_id="autocomplete_with_garage") + "?query={search}"
    TeamsUrl: Final[str] = KlaviaUrl + "/teams/{team_tag}"
    ShopsUrl: Final[str] = KlaviaUrl + "/shops"
    ShopSeasonUrl: Final[str] = ShopsUrl + "/season-shop"
    ShopDealsUrl: Final[str] = ShopsUrl + "/alices-deals"
    ShopItemsUrl: Final[str] = KlaviaUrl + "/shop_items/{item_id}"

    def __init__(self, username: str, password: str) -> None:
        self._session: Session = Crawler._login(username, password)

    def get_session(self) -> Session:
        return self._session

    def get_skins(self) -> None:
        response: Response = self._session.get("https://klavia.io/garage/cars/1495/view-car-skins")
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        # TODO: implement
        return

    def get_shop(self) -> Shop:
        shop_img_url_suffix: str = "/assets/shop-54d4e21a26f71965b2de774bfbf4a63b498bc3a2c53f06165c5aa152914cf06c.png"

        def get_section_offers(shop_section_url: str) -> list[ShopOffer]:
            response: Response = self._session.get(shop_section_url)
            soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
            offers_table: Tag = soup.find("div", attrs={"class": "row g-3"})
            offers: list[ShopOffer] = []
            for offer_div in offers_table.find_all("div", attrs={"class": "col-lg-6"}):
                img: Tag | None = offer_div.find("div", attrs={"class": "mb-3"}).find("img")
                img_url: str = img.get("src") if img else shop_img_url_suffix
                offers.append(
                    ShopOffer(
                        name=offer_div.find("h4").get_text().strip("\n").split("\n")[0],
                        price=int(offer_div.find("strong").get_text().replace(",", "")),
                        image_url=(Crawler.KlaviaUrl if img_url[0] == "/" else "") + img_url
                    )
                )
            return offers

        return Shop(
            seasonal_offers=get_section_offers(Crawler.ShopSeasonUrl),
            alices_deals=get_section_offers(Crawler.ShopDealsUrl)
        )

    def get_team(self, tag: str) -> Team:
        tag = tag.upper()
        response: Response = self._session.get(Crawler.TeamsUrl.format(team_tag=tag))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")

        name: str = soup.find("h1").get_text(strip=True)

        leader: UserIdentity
        agents: list[UserIdentity] = []
        members: list[UserIdentity] = []
        member_table: Tag = soup.find("table", attrs={"id": "tbl-daily-tracker"})
        member_table_body: Tag = member_table.find("tbody")
        for tr in member_table_body.find_all("tr"):
            racer: Tag; squad: Tag; joined: Tag; last_race: Tag; team_races: Tag  # noqa  Ugly, but type hints. :(
            racer, squad, joined, last_race, team_races = tr.find_all("td")[:5]
            # racer:
            racer_id: str = racer.find_all("a")[1]["href"].split("/")[-2]
            badge: Tag | None = racer.find("div", attrs={"class": "badge"})
            identity: UserIdentity = self.search_racer(racer_id)
            if identity:
                # Banned users result in an internal server error and don't have a valid identity:
                # https://klavia.io/racers/56230/garage (crooly - banned account)
                members.append(identity)
                if badge:
                    title = badge["title"]
                    if title == "Leader":
                        leader = identity
                    elif title == "Agent":
                        agents.append(identity)

        # noinspection PyUnboundLocalVariable
        return Team(
            name=name,
            tag=tag,
            leader=leader,
            agents=agents,
            members=members
        )

    def search_racers(self, search: str) -> list[UserIdentity]:
        response: Response = self._session.get(Crawler.SearchRacerUrl.format(search=search))
        data: list[tuple[int, str, str]] = response.json()
        # Sort by similarity to search string. (descending) Klavia's sorting is pretty random...
        data = sorted(data, key=lambda x: SequenceMatcher(None, x[2], search).real_quick_ratio(), reverse=True)
        return [
            UserIdentity(
                id=str(d[0]),
                display_name=d[1],
                username=d[2]
            ) for d in data
        ]

    def search_racer(self, search: str) -> UserIdentity | None:
        findings: list[UserIdentity] = self.search_racers(search)
        racer: UserIdentity | None = None
        if len(findings) > 0:
            racer = findings[0]
        return racer

    def get_quests(self, user_id: str) -> UserQuests:
        response: Response = self._session.get(Crawler.QuestsUrl.format(user_id=user_id))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        display_name: str = soup.select("#content > div.row.mb-3 > div.col-xl-6.d-flex > div > div > h3 > div.d-flex > div > div > span")[0].get_text(strip=True)

        quest_names: list[str] = [q.get_text(strip=True) for q in soup.find_all("h5", attrs={"class": "mb-3 color-title"}) if len]
        quest_progs: list[int] = [
            round(float(p.get("data-progress-percentage-value")))
            for p in soup.find_all("div", attrs={"data-controller": "progress"})
        ]
        quest_progress: list[UserQuestProgress] = [
            UserQuestProgress(
                Quest(
                    name=name
                ),
                progress=prog
            ) for name, prog in zip(quest_names, quest_progs)
        ]

        return UserQuests(
            user_id=user_id,
            display_name=display_name,
            quest_progress=quest_progress
        )

    def get_stats(self, user_id: str) -> UserStats:
        response: Response = self._session.get(Crawler.StatsUrl.format(user_id=user_id))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        username: str = soup.select("#content > div:nth-child(2) > div.col-xl-6.d-flex > div > div > h3 > div.d-flex > div > div > span")[0].get_text(strip=True)

        try:
            lifetime_races: int = int(
                soup
                .select("#content > div.row.mt-3.mb-3 > div:nth-child(2) > div > div > table > tbody > tr:nth-child(1) > td:nth-child(2)")[0]
                .get_text(strip=True)
                .split(" ")[0]
                .replace(",", "")
            )
            top_wpm: float = float(
                soup
                .select("#content > div.row.mt-3.mb-3 > div:nth-child(3) > div > div > table > tbody > tr:nth-child(2) > td:nth-child(2) > span")[0]
                .get_text(strip=True)
                .split(" ")[0]
            )
            perfect_acc: int = int(
                soup
                .select("#content > div.row.mt-3.mb-3 > div:nth-child(4) > div > div > table > tbody > tr:nth-child(2) > td:nth-child(2)")[0]
                .get_text(strip=True)
            )

            def get_minor_stat(label: str) -> str:
                for td in soup.find_all("td"):
                    if td.get_text(strip=True).startswith(label):
                        value_td = td.find_next_sibling("td")
                        if value_td:
                            return value_td.get_text(strip=True)
                return "-1"

            longest_session: int = int(get_minor_stat("Longest Session").split()[0].replace(",", ""))
            current_wpm: float = float(get_minor_stat("Current Speed").split()[0])
            current_acc: float = float(get_minor_stat("Current Accuracy").strip("%"))

            return UserStats(
                user_id=user_id,
                display_name=username,
                overview=UserStatOverview(
                    lifetime_races=lifetime_races,
                    longest_session=longest_session,
                    top_wpm=top_wpm,
                    current_wpm=current_wpm,
                    perfect_races=perfect_acc,
                    current_acc=current_acc
                )
            )
        except IndexError:
            # User might not have stats, yet.
            return UserStats(
                user_id=user_id,
                display_name=username,
                overview=UserStatOverview(
                    lifetime_races=0,
                    longest_session=0,
                    top_wpm=0,
                    current_wpm=0,
                    perfect_races=0,
                    current_acc=0
                )
            )

    def get_car(self, car_id: str) -> Car:
        response: Response = self._session.get(Crawler.CarInstanceUrl.format(car_id=car_id))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")

        name: str = soup.select("#car-info > table > tbody > tr:nth-child(5) > td:nth-child(2)")[0].get_text(strip=True)
        image_url: str = soup.select("#left-panel > div > div > canvas:nth-child(1)")[0]["data-show-vehicle-single-image-url-value"]

        return Car(
            name=name,
            image_url=image_url
        )

    def get_car_stats(self, car_id: str) -> CarStats:
        response: Response = self._session.get(Crawler.CarInstanceUrl.format(car_id=car_id))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")

        car_stats: CarStats
        try:
            stats_table = soup.select("#car-stats > table > tbody")[0]
            stats_data: ResultSet[Tag] = stats_table.find_all("td", attrs={"class": "text-end"})
            # noinspection PyCallingNonCallable
            car_stats = CarStats(
                races=int(stats_data[0].getText(strip=True)),
                dqs=int(stats_data[1].getText(strip=True)),
                avg_wpm=float(stats_data[2].getText(strip=True)),
                avg_acc=float(stats_data[3].getText(strip=True)[:-1]),
                top_wpm=float(stats_data[4].getText(strip=True)),
                top_acc=float(stats_data[5].getText(strip=True)[:-1]),
                perf_acc=int(stats_data[6].getText(strip=True))
            )
            pass
        except IndexError:
            # There are no stats available for this car. Maybe the owner never raced with it. Set default values:
            car_stats = CarStats(
                races=0,
                dqs=0,
                avg_wpm=0,
                avg_acc=0,
                top_wpm=0,
                top_acc=0,
                perf_acc=0
            )

        return car_stats

    def get_garage(self, user_id: str) -> Garage:
        response: Response = self._session.get(Crawler.GarageCarsUrl.format(user_id=user_id))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        username: str = soup.select("#content > div.row.mb-3 > div.col-xl-6.d-flex > div > div > h3 > div.d-flex > div > div > span")[0].get_text(strip=True)

        car_tags: ResultSet[Tag] = soup.find("tbody").find_all("tr")
        cars: list[Car] = [
            Car(
                name=row.find_all("td")[1].text,
                image_url=row.find("img").get("src")
            )
            for row in car_tags
        ]

        selected_car_id: str = soup.select("#equipped-car-frame > div > canvas:nth-child(1)")[0]["data-show-vehicle-car-id-value"]
        selected_car: Car = self.get_car(selected_car_id)
        cars.append(selected_car)
        selected_car_stats: CarStats = self.get_car_stats(selected_car_id)

        return Garage(
            user_id=user_id,
            display_name=username,
            cars=cars,
            selected_car=selected_car,
            selected_stats=selected_car_stats
        )

    def get_cars_dict(self) -> dict[str, Car]:
        response: Response = self._session.get(Crawler.LeaderboardsCarsUrl)
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        cars: dict[str, Car] = {}
        for car_tr in soup.find_all("tr")[1:]:
            image: Tag = car_tr.find("img")
            name: str = image.attrs["title"].strip()
            cars[name] = Car(
                name=name,
                image_url=image.attrs["src"]
            )
        return cars

    def get_cars(self) -> list[Car]:
        return list(self.get_cars_dict().values())

    @staticmethod
    def _login(username: str, password: str) -> Session:
        session: Session = Session()

        login_page: Response = session.get(Crawler.SignInUrl)
        login_soup: BeautifulSoup = BeautifulSoup(login_page.text, "html.parser")
        csrf_token: str = login_soup.find("meta", {"name": "csrf-token"})["content"]
        auth_token: str = login_soup.find("input", {"name": "authenticity_token"}).get("value")

        login_response: Response = session.post(
            url=Crawler.SignInUrl,
            headers={
                "x-csrf-token": csrf_token
            },
            data={
                "authenticity_token": auth_token,
                "racer[login]": username,
                "racer[password]": password,
                "racer[remember_me]": "0",
                "commit": "Sign+In"
            }
        )

        return session


if __name__ == '__main__':
    from dotenv import dotenv_values
    from pathlib import Path
    RootDir = Path(__file__).parent.parent.resolve()
    EnvVars: Final[dict[str, str]] = dotenv_values(RootDir / ".env")
    crawler: Crawler = Crawler(EnvVars["klavia_username_or_mail"], EnvVars["klavia_password"])
    user = "62812"
    # crawler.get_garage(user)
    # crawler.get_stats(user)
    # crawler.get_quests(user)
    # crawler.search_racers("")
    # crawler.get_team("vyn")
    # crawler.get_skins()
    crawler.get_shop()
