from abc import ABC
from enum import StrEnum
from threading import Lock
from dataclasses import dataclass
from json import load, dump
from pathlib import Path
from typing import Final


"""
Example persistence file:

{
    "servers": {
        "82839239": {  <- server id
            "verified_users": {
                "483993": {  <- discord user id
                    "klavia": "32893"  <- klavia user id
                }
            },
            "welcome_channel": "728245897",  <- welcome channel id
            "embed_author": "",  <- author of messages; some string
            "embed_icon_url": "",  <- icon of messages; some url to an image
            "linked_team": {  <- the linked Klavia team or None
                "tag": "VYN",  <- tag of linked team
                "settings": {  <- settings of team_link
                    "notify_events": [  <- Notification about these events should be sent to events channel
                        "New Member"    <- Example event, from enum -> Notify if new member joins the team on Klavia
                    ]
                },
                "events_channel": "728245897",  <- team events channel id
                "cached_state": {  <- cached mirror state of team to compare with in member change events, etc
                    "members": [  <- cached list of members
                        {
                            "id": "32893",  <- klavia id
                            "role": "Regular",  <- Role in team
                        }
                    ]
                }
            }
        }
    },
    "shop_offers": [  <- offers currently in the shop(s)
        "quest name 1",
        "quest name 2"
    ]
}

"""


class TeamEvent(StrEnum):
    NewMember = "NewMember"
    MemberLeft = "MemberLeft"
    Promotion = "Promotion"


@dataclass
class TeamLinkSettings:
    notify_events: list[TeamEvent]


class TeamMemberRole(StrEnum):
    Leader = "Leader"
    Agent = "Agent"
    Regular = "Regular"


@dataclass
class CachedTeamMember:
    id: str
    role: TeamMemberRole


@dataclass
class CachedTeamState:
    members: list[CachedTeamMember]


@dataclass
class TeamLink:
    tag: str
    settings: TeamLinkSettings
    events_channel: str | None
    cached_state: CachedTeamState | None


@dataclass
class User:
    id: str
    klavia_id: str


@dataclass
class Channel:
    id: str


@dataclass
class Server:
    id: str
    verified_users: list[User]
    welcome_channel: Channel | None
    embed_author: str
    embed_icon_url: str
    linked_team: TeamLink | None


@dataclass
class PersistentData:
    servers: list[Server]
    shop_offers: list[str]


class Persistence(ABC):
    RootDir: Final[Path] = Path(__file__).parent.parent.parent.resolve()
    PersistenceFile: Final[Path] = RootDir / "persistence.json"
    Encoding: Final[str] = "utf-8"
    Indent: Final[int] = 4
    FileLock: Final[Lock] = Lock()

    __Instance: PersistentData | None = None

    @staticmethod
    def get(force_reload: bool = False) -> PersistentData:
        if not Persistence.PersistenceFile.is_file():
            Persistence.write()

        if not force_reload and Persistence.__Instance is not None:
            return Persistence.__Instance

        with Persistence.FileLock:
            with open(Persistence.PersistenceFile, "r", encoding=Persistence.Encoding) as persistence:
                per: dict = load(persistence)
            Persistence.__Instance = PersistentData(
                servers=[
                    Server(
                        id=server[0],
                        verified_users=[
                            User(
                                id=user[0],
                                klavia_id=user[1]["klavia"]
                            ) for user in server[1]["verified_users"].items()
                        ] if "verified_users" in server[1] else [],
                        welcome_channel=Channel(
                            id=server[1]["welcome_channel"]
                        ),
                        embed_author=server[1]["embed_author"],
                        embed_icon_url=server[1]["embed_icon_url"],
                        linked_team=TeamLink(
                            tag=server[1]["linked_team"]["tag"],
                            settings=TeamLinkSettings(
                                notify_events=[
                                    TeamEvent(e) for e in server[1]["linked_team"]["settings"]["notify_events"]
                                ]
                            ),
                            events_channel=server[1]["linked_team"]["events_channel"],
                            cached_state=CachedTeamState(
                                members=[
                                    CachedTeamMember(
                                        id=m["id"],
                                        role=TeamMemberRole(m["role"])
                                    )
                                    for m in server[1]["linked_team"]["cached_state"]["members"]
                                    if "members" in server[1]["linked_team"]["cached_state"]
                                ]
                            ) if "cached_state" in server[1]["linked_team"] and
                                 server[1]["linked_team"]["cached_state"] else None
                        ) if "linked_team" in server[1] and server[1]["linked_team"] is not None else None
                    ) for server in per["servers"].items()
                ],
                shop_offers=per.get("shop_offers", [])
            )
        return Persistence.__Instance

    @staticmethod
    def get_server(server_id: str) -> Server:
        output: Server | None = None
        for server in Persistence.get().servers:
            if server.id == server_id:
                output = server
                break
        if output is None:
            # Create a new server and write it to persistence:
            output = Server(
                id=server_id,
                verified_users=[],
                welcome_channel=None,
                embed_author="",
                embed_icon_url="",
                linked_team=None
            )
            Persistence.__Instance.servers.append(output)
            Persistence.write()
        return output

    @staticmethod
    def write() -> None:
        with Persistence.FileLock:
            with open(Persistence.PersistenceFile, "w", encoding=Persistence.Encoding) as persistence:
                if Persistence.__Instance is None:
                    dump(
                        {
                            "servers": {

                            },
                            "shop_offers": [

                            ]
                        },
                        persistence,
                        indent=Persistence.Indent
                    )
                else:
                    dump(
                        {
                            "servers": {
                                server.id: {
                                    "verified_users": {
                                        user.id: {
                                            "klavia": user.klavia_id
                                        }
                                        for user in server.verified_users
                                    },
                                    "welcome_channel": server.welcome_channel.id if server.welcome_channel else None,
                                    "embed_author": server.embed_author,
                                    "embed_icon_url": server.embed_icon_url,
                                    "linked_team": {
                                        "tag": server.linked_team.tag,
                                        "settings": {
                                            "notify_events": [
                                                str(e) for e in server.linked_team.settings.notify_events
                                            ]
                                        },
                                        "events_channel": server.linked_team.events_channel,
                                        "cached_state": {
                                            "members": [
                                                {
                                                    "id": m.id,
                                                    "role": str(m.role)
                                                }
                                                for m in server.linked_team.cached_state.members
                                            ]
                                        } if server.linked_team.cached_state else None
                                    } if server.linked_team else None
                                }
                                for server in Persistence.__Instance.servers
                            },
                            "shop_offers": Persistence.__Instance.shop_offers
                        },
                        persistence,
                        indent=Persistence.Indent
                    )
        Persistence.get(force_reload=True)
