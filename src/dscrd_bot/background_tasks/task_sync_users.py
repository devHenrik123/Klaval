from asyncio import sleep

from discord import Bot, Guild, Forbidden

from dscrd_bot.commands.sync import sync
from dscrd_bot.persistent_data import Persistence


async def task_sync_users(bot: Bot) -> None:
    for server in Persistence.get().servers:
        guild: Guild = await bot.fetch_guild(int(server.id))
        for verified_user in server.verified_users:
            try:
                await sync(await guild.fetch_member(int(verified_user.id)))
            except Forbidden:
                print(f"Cannot sync! User: {verified_user.id} Guild: {guild.id}")
            await sleep(.01)  # Give bot some time to handle important work.
