from discord import Embed, Role
from discord.ext.commands import Context
from discord.utils import get

from dscrd_bot.embeds import OkayEmbed, ErrorType, ErrorEmbed
from dscrd_bot.roles import HeBotRole
from dscrd_bot.persistent_data import Persistence, Server


async def command_unverify(ctx: Context) -> None:
    await ctx.response.defer(ephemeral=True)
    server: Server = Persistence.get_server(str(ctx.guild.id))

    role_verified: Role = get(ctx.author.guild.roles, name=str(HeBotRole.Verified))
    role_unverified: Role = get(ctx.author.guild.roles, name=str(HeBotRole.Unverified))
    role_pending: Role = get(ctx.author.guild.roles, name=str(HeBotRole.VerificationPending))

    verified: bool = role_verified in ctx.author.roles
    pending: bool = role_pending in ctx.author.roles

    response: Embed
    if verified:
        # Persistence:
        server.verified_users = [u for u in server.verified_users if u.id != ctx.author.id]
        Persistence.write()

        # Roles
        await ctx.author.remove_roles(role_verified)
        await ctx.author.add_roles(role_unverified)

        response = OkayEmbed(
            title="Unverified",
            description=(
                f"{ctx.author.mention} "
                f"You are now unverified.\n"
                f"You may verify again using the **verify** command."
            ),
            custom_title=server.embed_author,
            author_icon_url=server.embed_icon_url
        )
    elif pending:
        response = ErrorEmbed(
            error_type=ErrorType.Permission,
            source=ctx.command.name,
            reason=(
                f"{ctx.author.mention} "
                f"You must wait for your verification process to finish, before you can unverify."
            ),
            custom_title=server.embed_author,
            author_icon_url=server.embed_icon_url
        )
    else:
        response = ErrorEmbed(
            error_type=ErrorType.Permission,
            source=ctx.command.name,
            reason=(
                f"{ctx.author.mention} "
                f"You must be verified before you can be unverified!"
            ),
            custom_title=server.embed_author,
            author_icon_url=server.embed_icon_url
        )

    await ctx.respond(
        embed=response,
        ephemeral=True
    )
