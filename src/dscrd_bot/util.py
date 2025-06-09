from pathlib import Path
from typing import Any, Final

from discord import Member, Role
from discord.ext.commands import Context, MissingPermissions, CommandError
from discord.utils import get
from dotenv import dotenv_values

from crawler import Crawler, UserIdentity
from dscrd_bot.embeds import ErrorEmbed, ErrorType
from dscrd_bot.persistent_data import Persistence
from dscrd_bot.roles import HeBotRole


BlankChar: Final[str] = "\u200b"
BlankLine: Final[str] = f"{BlankChar}\n"


RootDir: Path = Path(__file__).parent.parent.parent.resolve()
EnvVars: Final[dict[str, str]] = dotenv_values(RootDir / ".env")


def get_crawler() -> Crawler:
    return Crawler(EnvVars["klavia_username_or_mail"], EnvVars["klavia_password"])


def is_verified(discord_user: Member) -> bool:
    role_verified: Role = get(discord_user.guild.roles, name=HeBotRole.Verified)
    return role_verified in discord_user.roles


def get_klava_id(verified_discord_user: Member) -> str:
    for verified_user in Persistence.get_server(str(verified_discord_user.guild.id)).verified_users:
        if verified_user.id == str(verified_discord_user.id):
            return verified_user.klavia_id
    raise Exception("Cannot find Klavia ID")


async def error_handler(ctx: Context, error: CommandError) -> Any:
    if isinstance(error, MissingPermissions):
        await ctx.respond(
            embed=ErrorEmbed(
                error_type=ErrorType.Permission,
                source=ctx.command.name,
                reason=f"{ctx.author.mention} 🚫 You do not have sufficient permissions to use this command. 🚫"
            ),
            ephemeral=True
        )


async def verification_check_passed(ctx: Context, respond: bool = True) -> bool:
    verified: bool = is_verified(ctx.author)
    if not verified and respond:
        await ctx.respond(
            embed=ErrorEmbed(
                error_type=ErrorType.Permission,
                source=ctx.command.name,
                reason=(
                    f"{ctx.author.mention} "
                    f"You must be verified to use this command.\n"
                    f"Use the **/verify** command first."
                )
            ),
            ephemeral=True
        )
    return verified


async def get_identity(ctx: Context, klavia_name: str) -> UserIdentity | None:
    racer: UserIdentity | None = get_crawler().search_racer(klavia_name)
    if racer is None:
        await ctx.respond(
            embed=ErrorEmbed(
                error_type=ErrorType.Parameter,
                source=ctx.command.name,
                reason=f"{ctx.author.mention} Cannot find Klavia account of \"{klavia_name}\"."
            ),
            ephemeral=True
        )
    return racer


async def get_klavia_id_by_name(ctx: Context, klavia_name: str = "") -> str | None:
    klavia_id: str | None = None
    if klavia_name == "":
        klavia_id = get_klava_id(ctx.author)
    else:
        racer: UserIdentity | None = await get_identity(ctx, klavia_name)
        if racer is not None:
            klavia_id = racer.id
    return klavia_id
