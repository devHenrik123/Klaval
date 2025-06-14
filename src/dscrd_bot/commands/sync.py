from discord import Embed, Member
from discord.ext.commands import Context

from dscrd_bot.embeds import OkayEmbed
from dscrd_bot.persistent_data import Persistence, Server
from dscrd_bot.util import get_crawler, verification_check_passed, get_klava_id


async def sync(user: Member) -> None:
    klavia_id: str = get_klava_id(user)
    if user.id != user.guild.owner_id:
        # Cannot edit owner profile through bots. :(
        await user.edit(nick=get_crawler().get_garage(klavia_id).display_name)


async def command_sync(ctx: Context) -> None:
    await ctx.response.defer(ephemeral=True)
    server: Server = Persistence.get_server(str(ctx.guild.id))

    if not await verification_check_passed(ctx):
        return

    await sync(ctx.author)

    response: Embed = OkayEmbed(
        title="Synchronized",
        description=(
            f"{ctx.author.mention} "
            f"Your accounts have successfully been synchronized."
        ),
        custom_title=server.embed_author,
        author_icon_url=server.embed_icon_url
    )
    await ctx.respond(embed=response)
