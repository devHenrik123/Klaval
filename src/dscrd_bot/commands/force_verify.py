from discord import Member, Role
from discord.ext.commands import Context
from discord.utils import get

from dscrd_bot.embeds import OkayEmbed
from dscrd_bot.roles import HeBotRole
from dscrd_bot.persistent_data import Persistence, Server, User
from dscrd_bot.util import is_verified


async def command_force_verify(ctx: Context, user: Member, klavia_id: str) -> None:
    await ctx.response.defer(ephemeral=True)

    # Persistence:
    server: Server = Persistence.get_server(str(ctx.guild.id))
    if not is_verified(user):
        server.verified_users.append(
            User(
                id=str(user.id),
                klavia_id=klavia_id
            )
        )
    Persistence.write()

    # Assign roles:
    role_unverified: Role = get(user.guild.roles, name=HeBotRole.Unverified)
    role_verified: Role = get(user.guild.roles, name=HeBotRole.Verified)
    role_pending: Role = get(user.guild.roles, name=HeBotRole.VerificationPending)
    if role_unverified in user.roles:
        await user.remove_roles(role_unverified)
    if role_pending in user.roles:
        await user.remove_roles(role_pending)
    await user.add_roles(role_verified)

    await ctx.respond(
        embed=OkayEmbed(
            title="Verified",
            description=(
                f"{user.mention} has been force verified."
            ),
            custom_title=server.embed_author,
            author_icon_url=server.embed_icon_url
        ),
        ephemeral=True
    )
