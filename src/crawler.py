from dataclasses import dataclass
from re import search
from typing import Final, cast

from bs4 import BeautifulSoup, ResultSet
from bs4.element import Tag
from requests import Response, Session


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
    username: str
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
    username: str
    overview: UserStatOverview
    # Add more stats here!


@dataclass
class Garage:
    user_id: str
    username: str
    cars: list[Car]
    selected_car: Car
    selected_stats: CarStats


class Crawler:
    KlaviaUrl: Final[str] = "https://klavia.io"
    SignInUrl: Final[str] = KlaviaUrl + "/racers/sign_in"
    GarageUrl: Final[str] = KlaviaUrl + "/garages/{user_id}"
    RacerUrl: Final[str] = KlaviaUrl + "/racers/{user_id}"
    StatsUrl: Final[str] = RacerUrl + "/stats"
    QuestsUrl: Final[str] = RacerUrl + "/quests"
    LeaderboardsUrl: Final[str] = KlaviaUrl + "/leaderboards"
    TextsUrl: Final[str] = LeaderboardsUrl + "/texts"
    CarsUrl: Final[str] = LeaderboardsUrl + "/cars"

    def __init__(self, username: str, password: str) -> None:
        self._session: Session = Crawler._login(username, password)
        self._all_cars: dict[str, Car] = {c.name: c for c in self.get_cars()}

    def get_quests(self, user_id: str) -> UserQuests:
        response: Response = self._session.get(Crawler.QuestsUrl.format(user_id=user_id))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        username: str = search(r"\n(.*?)'s Quests\n", cast(Tag, soup.find("h3")).text).group(1)

        quest_names: list[str] = [q.text for q in soup.find_all("a", attrs={"data-turbo-frame": "modal"})]
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
            username=username,
            quest_progress=quest_progress
        )

    def get_stats(self, user_id: str) -> UserStats:
        response: Response = self._session.get(Crawler.StatsUrl.format(user_id=user_id))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        username: str = search(r"\n(.*?)'s Stats\n", cast(Tag, soup.find("h3")).text).group(1)

        if "This racer has not been ranked yet." in response.text:
            return UserStats(
                user_id=user_id,
                username=username,
                overview=UserStatOverview(
                    lifetime_races=0,
                    longest_session=0,
                    top_wpm=0,
                    current_wpm=0,
                    perfect_races=0,
                    current_acc=0
                )
            )

        main_stats: list[str] = [h.text.replace(",", "").strip("\n") for h in soup.find_all("h1")]
        longest_session: int = -1
        current_wpm: float = -1
        current_acc: float = - 1
        for p in soup.find_all("p"):
            if "Longest Session" in p.text:
                longest_session = int(search(r"Longest Session\n\n(.*?) races", p.text).group(1))
            elif "Current Speed (last 20 races)" in p.text:
                current_wpm = float(search(r"Current Speed \(last 20 races\)\n\n(.*?) WPM", p.text).group(1))
            elif "Current Accuracy (last 20 races)" in p.text:
                current_acc = float(search(r"Current Accuracy \(last 20 races\)\n\n(.*?)%", p.text).group(1))

        return UserStats(
            user_id=user_id,
            username=username,
            overview=UserStatOverview(
                lifetime_races=int(main_stats[0]),
                longest_session=longest_session,
                top_wpm=float(main_stats[1]),
                current_wpm=current_wpm,
                perfect_races=int(main_stats[2]),
                current_acc=current_acc
            )
        )

    def get_garage(self, user_id: str) -> Garage:
        response: Response = self._session.get(Crawler.GarageUrl.format(user_id=user_id))
        soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
        username: str = search(r"\n(.*?)'s Garage\n", cast(Tag, soup.find("h3")).text).group(1)
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
            username=username,
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
    """crawler: Crawler = Crawler("example@mail.com", "example")
    crawler.get_garage("63673")"""
