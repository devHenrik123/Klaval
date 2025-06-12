from discord import Embed
from discord.ext.commands import Context

from crawler import UserStats
from dscrd_bot.embeds import DefaultEmbed
from dscrd_bot.persistent_data import Persistence, Server
from dscrd_bot.util import verification_check_passed, get_crawler, get_klavia_id_by_name


async def command_stats(ctx: Context, klavia_name: str = "") -> None:
    await ctx.response.defer()
    server: Server = Persistence.get_server(str(ctx.guild.id))

    if not await verification_check_passed(ctx):
        return

    klavia_id: str | None = await get_klavia_id_by_name(ctx, klavia_name)
    if klavia_id is None:
        return

    stat_data: UserStats = get_crawler().get_stats(klavia_id)
    response: Embed = DefaultEmbed(
        title=f"{stat_data.display_name}'s Stats:",
        custom_title=server.embed_author,
        author_icon_url=server.embed_icon_url
    )
    response.add_field(
        name="",
        value=(
            "Lifetime Races:\n"
            "Longest Session:\n"
            "Top WPM:\n"
            "Current WPM:\n"
            "Perfect Races:\n"
            "Current Accuracy:\n"
        ),
        inline=True
    )
    response.add_field(
        name="",
        value=(
            f"{stat_data.overview.lifetime_races}\n"
            f"{stat_data.overview.longest_session}\n"
            f"{stat_data.overview.top_wpm}\n"
            f"{stat_data.overview.current_wpm}\n"
            f"{stat_data.overview.perfect_races}\n"
            f"{stat_data.overview.current_acc}%\n"
        ),
        inline=True
    )
    await ctx.respond(embed=response)
