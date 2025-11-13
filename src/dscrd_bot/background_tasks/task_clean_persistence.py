from asyncio import sleep
from copy import copy

from discord import Bot, Forbidden, HTTPException

from dscrd_bot.persistent_data import Persistence


async def task_clean_persistence(bot: Bot) -> None:
    for server in copy(Persistence.get().servers):
        try:
            # Check if guild is available:
            await bot.fetch_guild(int(server.id))
        except Forbidden as ex:
            print(f"Can not access server {server.id}. Removing it from persistence! ", ex)
            Persistence.get().servers.remove(server)
        except HTTPException as ex:
            print(f"Can not find discord server {server.id}. Removing it from persistence! ", ex)
            Persistence.get().servers.remove(server)

        await sleep(.01)  # Give bot some time to handle important work.

    Persistence.write()
