from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Final

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


class Crawler:
    KlaviaUrl: Final[str] = "https://klavia.io"
    SignInUrl: Final[str] = KlaviaUrl + "/racers/sign_in"
    RacerUrl: Final[str] = KlaviaUrl + "/racers/{user_id}"
    GarageUrl: Final[str] = RacerUrl + "/garage"
    StatsUrl: Final[str] = RacerUrl + "/stats"
    QuestsUrl: Final[str] = RacerUrl + "/quests"
    LeaderboardsUrl: Final[str] = KlaviaUrl + "/leaderboards"
    TextsUrl: Final[str] = LeaderboardsUrl + "/texts"
    CarsUrl: Final[str] = LeaderboardsUrl + "/cars"
    SearchRacerUrl: Final[str] = RacerUrl.format(user_id="autocomplete_with_garage") + "?query={search}"

    def __init__(self, username: str, password: str) -> None:
        self._session: Session = Crawler._login(username, password)
        self._all_cars: dict[str, Car] = {c.name: c for c in self.get_cars()}

    def search_racers(self, search: str) -> list[UserIdentity]:
        response: Response = self._session.get(Crawler.SearchRacerUrl.format(search=search))
        data: list[tuple[int, str, str]] = response.json()
        # Sort by similarity to search string. (descending) Klavia's sorting is pretty random...
        data = sorted(data, key=lambda x: SequenceMatcher(None, x, search).real_quick_ratio())
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
        username: str = soup.find("h3").get_text(strip=True)

        quest_names: list[str] = [q.text for q in soup.find_all("a", attrs={"data-turbo-frame": "modal"}) if len]
        try:
            quest_names[0] = soup.find("h5").get_text(strip=True)
        except AttributeError:
            pass  # No active quest! -> ignore
        quest_progs: list[int] = [
            int(p.get("data-progress-percentage-value"))
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
            display_name=username,
            quest_progress=quest_progress
        )

    def get_stats(self, user_id: str) -> UserStats:
        response: Response = self._session.get(Crawler.RacerUrl.format(user_id=user_id))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        username: str = soup.find("h3").get_text(strip=True)

        try:
            main_stats: list[Tag] = soup.find_all("strong")
            lifetime_races: int = int(main_stats[0].get_text(strip=True).split(" ")[0].replace(",", ""))
            top_wpm: float = float(main_stats[1].get_text(strip=True).split(" ")[0])
            perfect_acc: int = int(main_stats[2].get_text(strip=True))

            def get_minor_stat(s: BeautifulSoup, label: str) -> str:
                for td in soup.find_all("td"):
                    if td.get_text(strip=True).startswith(label):
                        value_td = td.find_next_sibling("td")
                        if value_td:
                            return value_td.get_text(strip=True)
                return "-1"

            longest_session: int = int(get_minor_stat(soup, "Longest Session").split()[0].replace(",", ""))
            current_wpm: float = float(get_minor_stat(soup, "Current Speed").split()[0])
            current_acc: float = float(get_minor_stat(soup, "Current Accuracy").strip("%"))

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

    def get_garage(self, user_id: str) -> Garage:
        response: Response = self._session.get(Crawler.GarageUrl.format(user_id=user_id))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        username: str = soup.find("h3").get_text(strip=True)
        cars: list[Car] = []
        for car_tag in soup.find_all("a", attrs={"data-turbo-frame": "selected_car"}):
            name: str = car_tag.get("title").split("|")[0].strip()
            car: Car | None = self._all_cars.get(name, None)
            if car:
                cars.append(car)
            else:
                # Cannot find car -> Ignore for now
                # Might do some error logging in the future...
                pass
        selected_car: Car = self._all_cars[
            soup
            .find("div", id="selected_car")
            .find("div", class_="card-header")
            .find(text=True, recursive=False)
            .strip()
        ]

        try:
            selected_stats_table: Tag = soup.find("tbody")
            selected_stats_elems: ResultSet[Tag] = selected_stats_table.find_all("td", attrs={"class": "text-end"})

            # noinspection PyCallingNonCallable
            selected_stats: CarStats = CarStats(
                races=int(selected_stats_elems[0].getText(strip=True)),
                dqs=int(selected_stats_elems[1].getText(strip=True)),
                avg_wpm=float(selected_stats_elems[2].getText(strip=True)),
                avg_acc=float(selected_stats_elems[3].getText(strip=True)[:-1]),
                top_wpm=float(selected_stats_elems[4].getText(strip=True)),
                top_acc=float(selected_stats_elems[5].getText(strip=True)[:-1]),
                perf_acc=int(selected_stats_elems[6].getText(strip=True))
            )
        except AttributeError:
            # User might have no stats, yet.
            selected_stats: CarStats = CarStats(
                races=0,
                dqs=0,
                avg_wpm=0,
                avg_acc=0,
                top_wpm=0,
                top_acc=0,
                perf_acc=0
            )

        return Garage(
            user_id=user_id,
            display_name=username,
            cars=cars,
            selected_car=selected_car,
            selected_stats=selected_stats
        )

    def get_cars(self) -> list[Car]:
        if hasattr(self, "_all_cars"):
            return list(self._all_cars.values())

        response: Response = self._session.get(Crawler.CarsUrl)
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        cars: list[Car] = []
        for car_tr in soup.find_all("tr")[1:]:
            image: Tag = car_tr.find("img")
            cars.append(
                Car(
                    image.attrs["title"].strip(),
                    image.attrs["src"]
                )
            )
        return cars

    @staticmethod
    def _login(username: str, password: str) -> Session:
        session: Session = Session()

        login_page: Response = session.get(Crawler.KlaviaUrl)
        login_soup: BeautifulSoup = BeautifulSoup(login_page.text, "html.parser")
        csrf_token: str = login_soup.find("meta", {"name": "csrf-token"})["content"]

        login_response: Response = session.post(
            url=Crawler.SignInUrl,
            data={
                "authenticity_token": csrf_token,
                "racer[email]": username,
                "racer[password]": password,
                "racer[remember_me]": "0",
                "commit": "Sign+In"
            }
        )

        return session


if __name__ == '__main__':
    """from dotenv import dotenv_values
    from pathlib import Path
    RootDir = Path(__file__).parent.parent.resolve()
    EnvVars: Final[dict[str, str]] = dotenv_values(RootDir / ".env")
    crawler: Crawler = Crawler(EnvVars["klavia_username_or_mail"], EnvVars["klavia_password"])
    user = "62812"
    # crawler.get_garage(user)
    # crawler.get_stats(user)
    # crawler.get_quests(user)
    crawler.search_racers("")"""
