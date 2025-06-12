from discord import Member, Role
from discord.ext.commands import Context
from discord.utils import get

from dscrd_bot.embeds import OkayEmbed
from dscrd_bot.roles import HeBotRole
from dscrd_bot.persistent_data import Persistence, Server
from dscrd_bot.util import is_verified


async def command_force_unverify(ctx: Context, user: Member) -> None:
    await ctx.response.defer(ephemeral=True)
    server: Server = Persistence.get_server(str(ctx.guild.id))

    if is_verified(user):
        # Persistence:
        server.verified_users = [u for u in server.verified_users if u.id != user.id]
        Persistence.write()

        # Roles
        role_verified: Role = get(ctx.author.guild.roles, name=str(HeBotRole.Verified))
        role_unverified: Role = get(ctx.author.guild.roles, name=str(HeBotRole.Unverified))
        await ctx.author.remove_roles(role_verified)
        await ctx.author.add_roles(role_unverified)

    response = OkayEmbed(
        title="Unverified",
        description=(
            f"{ctx.author.mention} successfully unverified {user.mention}.\n"
        ),
        custom_title=server.embed_author,
        author_icon_url=server.embed_icon_url
    )
    await ctx.respond(embed=response, ephemeral=True)
