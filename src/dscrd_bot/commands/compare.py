from discord import Embed
from discord.ext.commands import Context

from crawler import Garage, UserStats, Crawler
from dscrd_bot.embeds import DefaultEmbed
from dscrd_bot.persistent_data import Persistence, Server
from dscrd_bot.util import verification_check_passed, get_klavia_id_by_name, get_klava_id, get_crawler


async def command_compare(ctx: Context, klavia_name_one: str, klavia_name_two: str = "") -> None:
    await ctx.response.defer()
    server: Server = Persistence.get_server(str(ctx.guild.id))

    if not await verification_check_passed(ctx):
        return

    user_ids: list[str] = [await get_klavia_id_by_name(ctx, n) for n in [klavia_name_one, klavia_name_two] if len(n.strip()) > 0]
    if len(user_ids) == 1:
        user_ids = [get_klava_id(ctx.author)] + user_ids

    response: Embed = DefaultEmbed(
        title=f"Racer Comparison:",
        custom_title=server.embed_author,
        author_icon_url=server.embed_icon_url
    )

    response.add_field(
        name="Stats",
        value="Cars:\n"
              "Races:\n"
              "Longest Session:\n"
              "Top WPM:\n"
              "Perfect Races:\n"
              "Current WPM:\n"
              "Current Accuracy:\n",
        inline=True
    )

    crawler: Crawler = get_crawler()
    for index, user_id in enumerate(user_ids):
        garage: Garage = crawler.get_garage(user_id)
        stats: UserStats = crawler.get_stats(user_id)

        response.add_field(
            name=garage.display_name + ("" if index != 0 else "   VS"),
            value=f"{len(garage.cars)}\n"
                  f"{stats.overview.lifetime_races}\n"
                  f"{stats.overview.longest_session}\n"
                  f"{stats.overview.top_wpm}\n"
                  f"{stats.overview.perfect_races}\n"
                  f"{stats.overview.current_wpm}\n"
                  f"{stats.overview.current_acc}\n",
            inline=True
        )

    await ctx.respond(embed=response)
