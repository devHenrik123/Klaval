from discord import Embed
from discord.ext.commands import Context

from crawler import UserIdentity, Crawler
from dscrd_bot.embeds import DefaultEmbed
from dscrd_bot.persistent_data import Persistence, Server
from dscrd_bot.util import get_crawler


async def command_find_racer(ctx: Context, klavia_name: str) -> None:
    await ctx.response.defer()
    server: Server = Persistence.get_server(str(ctx.guild.id))

    max_display: int = 10

    users: list[UserIdentity] = get_crawler().search_racers(klavia_name)

    response: Embed = DefaultEmbed(
        title=f"User Search",
        description=(
            f"{ctx.author.mention}\n"
            f"Found {len(users)} matching Klavia account{'s' if len(users) != 1 else ''}.\n"
        ),
        custom_title=server.embed_author,
        author_icon_url=server.embed_icon_url
    )

    if len(users) > max_display:
        users = users[:max_display]

    ids: str = "\n".join([f"[{u.id}]({Crawler.RacerUrl.format(user_id=u.id)})" for u in users])
    display_names: str = "\n".join([u.display_name for u in users])
    usernames: str = "\n".join([u.username for u in users])

    response.add_field(
        name="",
        value=(
            f"**ID**\n{ids}"
        ),
        inline=True
    )
    response.add_field(
        name="",
        value=(
            f"**Display Name**\n{display_names}"
        ),
        inline=True
    )
    response.add_field(
        name="",
        value=(
            f"**Username**\n{usernames}"
        ),
        inline=True
    )

    await ctx.respond(embed=response)
