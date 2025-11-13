from typing import Callable, Final

from _pytest.fixtures import fixture

# We need "src.crawler" instead of "crawler" and have to add src to PYTHONPATH when running tests,
# because otherwise python will import classes twice as different instances.
# That would break the isinstance methode. Dumbest language design I've ever seen!!!
from src.crawler import Crawler, Team, UserIdentity, UserQuests, UserStats, Garage, Car, UserStatOverview, Shop, \
    ShopOffer
from tests.utils import EnvVars


UserID_Nusakan: Final[str] = "43"


@fixture
def crawler() -> Crawler:
    return Crawler(
        username=EnvVars["klavia_username_or_mail"],
        password=EnvVars["klavia_password"]
    )


def test_login(crawler: Crawler) -> None:
    assert crawler.get_session().get(Crawler.LeaderboardsUrl).status_code == 200


def test_get_shop(crawler: Crawler) -> None:
    shop: Shop = crawler.get_shop()
    assert isinstance(shop, Shop)
    assert isinstance(shop.seasonal_offers, list)
    assert isinstance(shop.alices_deals, list)
    assert all(isinstance(o, ShopOffer) for o in shop.seasonal_offers)
    assert all(isinstance(o, ShopOffer) for o in shop.alices_deals)


def test_get_team(crawler: Crawler) -> None:
    tag: str = "vyn"
    team: Team = crawler.get_team(tag)
    assert isinstance(team, Team)
    assert team.tag == tag.upper()
    assert team.leader is not None
    assert isinstance(team.members, list) and len(team.members) > 0


def test_get_team_no_duplicate_members(crawler: Crawler) -> None:
    tag: str = "vyn"
    team: Team = crawler.get_team(tag)
    assert all([len([x for x in team.members if x.id == m.id]) == 1 for m in team.members])


def test_search_racers(crawler: Crawler) -> None:
    racers: list[UserIdentity] = crawler.search_racers("Nusakan")
    contains_racer: Callable[[None], bool] = lambda username: any(r for r in racers if r.username == username)
    assert contains_racer("nusakan")
    assert contains_racer("nusakanistesting")


def test_search_racer(crawler: Crawler) -> None:
    racer: UserIdentity = crawler.search_racer("Nusakan")
    assert racer.username == "nusakan"


def test_get_quests(crawler: Crawler) -> None:
    quests: UserQuests = crawler.get_quests(UserID_Nusakan)
    assert isinstance(quests, UserQuests)


def test_get_stats(crawler: Crawler) -> None:
    stats: UserStats = crawler.get_stats(UserID_Nusakan)
    assert isinstance(stats, UserStats)
    assert isinstance(stats.overview, UserStatOverview)


def test_get_garage(crawler: Crawler) -> None:
    user_id: str = UserID_Nusakan
    garage: Garage = crawler.get_garage(user_id)
    assert isinstance(garage, Garage)
    assert garage.user_id == user_id
    assert isinstance(garage.cars.pop(), Car)
    assert isinstance(garage.selected_car, Car)


def test_get_cars_dict(crawler: Crawler) -> None:
    cars: dict[str, Car] = crawler.get_cars_dict()
    assert isinstance(cars, dict)
    assert len(cars.items()) > 0
    assert all(isinstance(k, str) for k in cars.keys())
    assert all(isinstance(v, Car) for v in cars.values())


def test_get_cars(crawler: Crawler) -> None:
    cars: list[Car] = crawler.get_cars()
    assert isinstance(cars, list)
    assert len(cars) > 0
    assert all(isinstance(c, Car) for c in cars)
