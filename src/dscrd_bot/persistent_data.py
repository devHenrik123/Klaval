from abc import ABC
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
            "welcome_channel": "728245897"  <- welcome channel id
        }
    }
}

"""


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


@dataclass
class PersistentData:
    servers: list[Server]


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
                        ) if "welcome_channel" in server[1] else None,
                        embed_author=server[1]["embed_author"],
                        embed_icon_url=server[1]["embed_icon_url"]
                    ) for server in per["servers"].items()
                ]
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
                embed_icon_url=""
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

                            }
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
                                    "welcome_channel": server.welcome_channel.id if server.welcome_channel is not None else None,
                                    "embed_author": server.embed_author,
                                    "embed_icon_url": server.embed_icon_url
                                }
                                for server in Persistence.__Instance.servers
                            }
                        },
                        persistence,
                        indent=Persistence.Indent
                    )
        Persistence.get(force_reload=True)
