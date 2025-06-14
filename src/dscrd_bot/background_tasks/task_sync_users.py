from asyncio import sleep

from discord import Bot, Guild

from dscrd_bot.commands.sync import sync
from dscrd_bot.persistent_data import Persistence


async def task_sync_users(bot: Bot) -> None:
    for server in Persistence.get().servers:
        guild: Guild = await bot.fetch_guild(int(server.id))
        for verified_user in server.verified_users:
            await sync(await guild.fetch_member(int(verified_user.id)))
            await sleep(.01)  # Give bot some time to handle important work.
