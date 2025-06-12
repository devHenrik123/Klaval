from math import floor

from discord import Embed
from discord.ext.commands import Context

from crawler import UserQuests
from dscrd_bot.embeds import DefaultEmbed
from dscrd_bot.persistent_data import Persistence, Server
from dscrd_bot.util import verification_check_passed, get_crawler, get_klavia_id_by_name


async def command_quests(ctx: Context, klavia_name: str = "") -> None:
    await ctx.response.defer()
    server: Server = Persistence.get_server(str(ctx.guild.id))

    if not await verification_check_passed(ctx):
        return

    klavia_id: str | None = await get_klavia_id_by_name(ctx, klavia_name)
    if klavia_id is None:
        return

    quest_data: UserQuests = get_crawler().get_quests(klavia_id)
    response: Embed = DefaultEmbed(
        title=f"{quest_data.display_name}'s Quests:",
        custom_title=server.embed_author,
        author_icon_url=server.embed_icon_url
    )

    def prog_bar(progress: int) -> str:
        max_len: int = 10
        prog: int = floor(progress / 100 * max_len)
        return (prog * "●") + ((max_len - prog) * "○")

    response.add_field(
        name="",
        value="".join([f"{qp.quest.name}\n" for qp in quest_data.quest_progress]),
        inline=True
    )
    response.add_field(
        name="",
        value="".join([f"{prog_bar(qp.progress)}\n" for qp in quest_data.quest_progress]),
        inline=True
    )
    response.add_field(
        name="",
        value="".join(f"{qp.progress}%\n" for qp in quest_data.quest_progress),
        inline=True
    )
    await ctx.respond(embed=response)
