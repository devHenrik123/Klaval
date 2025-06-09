import string
from asyncio import sleep
from math import floor
from pathlib import Path
from random import choice
from re import search
from time import time
from typing import Any, Final

from discord import Member, Intents, Embed, Bot, HTTPException, Role, TextChannel
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ext.commands import Context, MissingPermissions, CommandError
from discord.utils import get
from dotenv import dotenv_values

from crawler import Crawler, Garage, Car, UserStats, UserQuests
from dscrd_bot.embeds import DefaultEmbed, OkayEmbed, ErrorType, ErrorEmbed
from dscrd_bot.roles import HeBotRole
from src.dscrd_bot.persistent_data import Persistence, Server, Channel, User

BlankChar: Final[str] = "\u200b"
BlankLine: Final[str] = f"{BlankChar}\n"

RootDir: Path = Path(__file__).parent.parent.resolve()
EnvVars: Final[dict[str, str]] = dotenv_values(RootDir / ".env")


def get_crawler() -> Crawler:
    return Crawler(EnvVars["klavia_username_or_mail"], EnvVars["klavia_password"])


def is_verified(discord_user: Member) -> bool:
    role_verified: Role = get(discord_user.guild.roles, name=HeBotRole.Verified)
    return role_verified in discord_user.roles


def get_klava_id(discord_user: Member) -> str:
    for verified_user in Persistence.get_server(str(discord_user.guild.id)).verified_users:
        if verified_user.id == discord_user:
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
            )
        )
    return verified


def main() -> None:
    intents: Intents = Intents(
        guilds=True,
        messages=True,
        message_content=True,
        members=True
    )
    bot: Bot = Bot(intents=intents)

    @bot.event
    async def on_member_join(member: Member) -> Any:
        server: Server = Persistence.get_server(str(member.guild.id))
        welcome_channel: GuildChannel = bot.get_channel(int(server.welcome_channel.id))
        role_unverified: Role = get(member.guild.roles, name=HeBotRole.Unverified)
        await member.add_roles(role_unverified)
        embed: Embed = DefaultEmbed(
            f"Welcome {member.display_name}!",
            description=(
                f"{member.mention} Please verify your Klavia account to gain access to all channels.\n"
                f"To do so, use the **/verify** command. "
                f"The **/verify** command requires your **Klavia ID**. Your Klavia ID can be found in the "
                "url, when changing your account settings."
            )
        )
        await welcome_channel.send("", embed=embed)

    @bot.event
    async def on_member_remove(member: Member) -> Any:
        if is_verified(member):
            # Remove member from persistence:
            server: Server = Persistence.get_server(str(member.guild.id))
            server.verified_users = [u for u in server.verified_users if u.id != str(member.id)]
            Persistence.write()
        await bot.get_channel(int(Persistence.get_server(str(member.guild.id)).welcome_channel.id)).send(embed=DefaultEmbed(
            title="User Left",
            description=(
                f"{member.mention} has left the server."
            )
        ))

    @commands.has_permissions(administrator=True)
    @bot.slash_command(description="Force a user verification. Can only be used by admins.")
    async def force_verify(ctx: Context, user: Member, klavia_id: str) -> Any:
        await ctx.response.defer()

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

        await ctx.respond(embed=OkayEmbed(
            title="Verified",
            description=(
                f"{user.mention} has been force verified."
            )
        ))

    @force_verify.error
    async def force_verify_error(ctx: Context, error: CommandError) -> Any:
        await error_handler(ctx, error)

    @commands.has_permissions(administrator=True)
    @bot.slash_command(description="Setup command of the bot. Sets channels and creates necessary roles, etc.")
    async def setup(ctx: Context, welcome_channel: TextChannel) -> Any:
        await ctx.response.defer()

        # Set welcome channel:
        server: Server = Persistence.get_server(str(ctx.guild.id))
        server.welcome_channel = Channel(id=str(welcome_channel.id))
        Persistence.write()

        # Create roles:
        existing_roles: list[str] = [r.name for r in ctx.guild.roles]
        new_roles: list[HeBotRole] = [e for e in HeBotRole if e not in existing_roles]
        for role in new_roles:
            await ctx.guild.create_role(name=role)

        await ctx.respond(
            embed=OkayEmbed(
                title="Setup Finished",
                description="".join([
                    f"{ctx.author.mention}\n",
                    f"Successfully finished the setup.\n",
                    f"The welcome channel has been set to: {welcome_channel.name}\n"
                    f"Created {len(new_roles)} new roles.\n",
                    "".join([f"- {r}\n" for r in new_roles]),
                    f"Thank you for using Henriks Bot!"
                ])
            )
        )

    @setup.error
    async def setup_error(ctx: Context, error: CommandError) -> Any:
        await error_handler(ctx, error)

    @bot.slash_command(description="Show a users current quests.")
    async def quests(ctx: Context, klavia_id: str = "") -> Any:
        await ctx.response.defer()

        if klavia_id == "":
            if not await verification_check_passed(ctx):
                return
            else:
                klavia_id = get_klava_id(ctx.author)

        quest_data: UserQuests = get_crawler().get_quests(klavia_id)
        response: Embed = DefaultEmbed(
            title=f"{quest_data.username}'s Quests"
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

    @bot.slash_command(description="Show a users stats.")
    async def stats(ctx: Context, klavia_id: str = "") -> Any:
        await ctx.response.defer()

        if klavia_id == "":
            if not await verification_check_passed(ctx):
                return
            else:
                klavia_id = get_klava_id(ctx.author)

        stat_data: UserStats = get_crawler().get_stats(klavia_id)
        response: Embed = DefaultEmbed(
            title=f"{stat_data.username}'s Stats"
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
                f"{stat_data.overview.lifetime_races} races\n"
                f"{stat_data.overview.longest_session} races\n"
                f"{stat_data.overview.top_wpm} wpm\n"
                f"{stat_data.overview.current_wpm} wpm\n"
                f"{stat_data.overview.perfect_races} races\n"
                f"{stat_data.overview.current_acc}%\n"
            ),
            inline=True
        )
        await ctx.respond(embed=response)

    @bot.slash_command(description="Show a users garage.")
    async def garage(ctx: Context, klavia_id: str = "") -> Any:
        await ctx.response.defer()

        if klavia_id == "":
            if not await verification_check_passed(ctx):
                return
            else:
                klavia_id = get_klava_id(ctx.author)

        garage_data: Garage = get_crawler().get_garage(klavia_id)

        def cars(cols: int) -> list[list[Car]]:
            output: list[list[Car]] = [[] for _ in range(cols)]
            for i, car in enumerate(garage_data.cars):
                output[i % cols].append(car)
            return output

        response: Embed = DefaultEmbed(
            title=f"{garage_data.username}'s Garage",
            description="".join([
                BlankLine,
                f"**Owned cars:** {len(garage_data.cars)}\n"
            ]),
            thumbnail=garage_data.selected_car.image_url,
            image=garage_data.selected_car.image_url
        )
        for car_list in cars(3):
            response.add_field(
                name="",
                value="".join([f"{c.name}\n" for c in car_list]),
                inline=True
            )
        response.add_field(name="", value=BlankLine, inline=False)
        response.add_field(
            name="",
            value=(
                f"**Selected Car:** {garage_data.selected_car.name}\n"
            ),
            inline=False
        )
        response.add_field(
            name="",
            value=(
                "Races:\n"
                "DQs:\n"
                "Avg WPM:\n"
                "Avg Accuracy:\n"
                "Top WPM:\n"
                "Top Accuracy\n"
                "Perfect Accuracy:\n"
            ),
            inline=True
        )
        response.add_field(
            name="",
            value=(
                f"{garage_data.selected_stats.races}\n"
                f"{garage_data.selected_stats.dqs}\n"
                f"{garage_data.selected_stats.avg_wpm}\n"
                f"{garage_data.selected_stats.avg_acc}%\n"
                f"{garage_data.selected_stats.top_wpm}\n"
                f"{garage_data.selected_stats.top_acc}%\n"
                f"{garage_data.selected_stats.perf_acc}\n"
            ),
            inline=True
        )
        await ctx.respond(embed=response)

    @bot.slash_command(description="Verify your account by linking it to your Klavia profile.")
    async def verify(ctx: Context, user_id: str) -> Any:
        await ctx.response.defer()
        response: Embed = DefaultEmbed(
            title="Verified",
            description="You have already been verified."
        )

        role_verified: Role = get(ctx.author.guild.roles, name=str(HeBotRole.Verified))
        role_unverified: Role = get(ctx.author.guild.roles, name=str(HeBotRole.Unverified))
        role_pending: Role = get(ctx.author.guild.roles, name=str(HeBotRole.VerificationPending))

        verified: bool = role_verified in ctx.author.roles
        pending: bool = role_pending in ctx.author.roles

        polling_rate: int = 30  # check for verification every <polling_rate> seconds
        timeout: int = 60 * 5  # verification timeout in seconds
        min_verification_time: str = f"Verification will take a minimum of {polling_rate} seconds."

        if pending:
            response = DefaultEmbed(
                title="Pending Verification",
                description="".join([
                    f"{ctx.author.mention} ",
                    f"You are currently being verified. Please be patient.\n",
                    min_verification_time
                ])
            )
        elif not verified:
            initial_name: str = get_crawler().get_garage(user_id).username
            random_name: str = "".join(choice(string.ascii_letters) for _ in range(12))
            await ctx.respond(
                embed=DefaultEmbed(
                    title="Verification",
                    description="".join([
                        f"{ctx.author.mention} ",
                        f"Please change your Klavia display name to **{random_name}** to verify your account.\n",
                        min_verification_time
                    ])
                )
            )
            await ctx.author.add_roles(role_pending)

            start_time: float = time()
            timed_out: bool = False
            while not verified and not timed_out:
                await sleep(polling_rate)
                name: str = get_crawler().get_garage(user_id).username

                if name == random_name:
                    verified = True

                    # Persistence:
                    server: Server = Persistence.get_server(str(ctx.guild.id))
                    server.verified_users.append(
                        User(
                            id=str(ctx.author.id),
                            klavia_id=user_id
                        )
                    )
                    Persistence.write()

                    # Roles:
                    await ctx.author.remove_roles(role_unverified)
                    await ctx.author.add_roles(role_verified)
                    if ctx.author != ctx.guild.owner:
                        # Cannot edit owner profile through bots.
                        await ctx.author.edit(nick=initial_name)

                timed_out = time() >= start_time + timeout

            await ctx.author.remove_roles(role_pending)

            if verified:
                response = OkayEmbed(
                    title="Verified",
                    description=(
                        f"{ctx.author.mention} "
                        f"You have been verified. You may now change your Klavia display name to whatever you like.\n"
                        f"You can update your server name using the **sync**-command."
                    )
                )
            else:
                response = ErrorEmbed(
                    error_type=ErrorType.Timeout,
                    source=ctx.command.name,
                    reason=(
                        f"{ctx.author.mention}"
                        f"Cannot verify your account.\n"
                        f"Please try again later and make sure to change your Klavia display name accordingly."
                    )
                )

        try:
            await ctx.respond(embed=response)
        except HTTPException:  # invalid / expired token
            await ctx.send(embed=response)

    @bot.slash_command(description="Synchronize your Discord profile with your Klavia account.")
    async def sync(ctx: Context) -> Any:
        await ctx.response.defer()

        if not await verification_check_passed(ctx):
            return

        klavia_id: str = get_klava_id(ctx.author)
        if ctx.author != ctx.guild.owner:
            # Cannot edit owner profile through bots. :(
            await ctx.author.edit(nick=get_crawler().get_garage(klavia_id).username)

        response: Embed = OkayEmbed(
            title="Synchronized",
            description=(
                f"{ctx.author.mention} "
                f"Your accounts have successfully been synchronized."
            )
        )
        await ctx.respond(embed=response)

    @commands.has_permissions(administrator=True)
    @bot.slash_command(description="Force unverify a user.")
    async def force_unverify(ctx: Context, user: Member) -> Any:
        await ctx.response.defer()
        if is_verified(user):
            # Persistence:
            server: Server = Persistence.get_server(str(ctx.guild.id))
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
            )
        )
        await ctx.respond(embed=response)

    @force_unverify.error
    async def force_unverify_error(ctx: Context, error: CommandError) -> Any:
        await error_handler(ctx, error)


    @bot.slash_command(description="Unlink your Klavia account from your Discord profile.")
    async def unverify(ctx: Context) -> Any:
        await ctx.response.defer()

        role_verified: Role = get(ctx.author.guild.roles, name=str(HeBotRole.Verified))
        role_unverified: Role = get(ctx.author.guild.roles, name=str(HeBotRole.Unverified))
        role_pending: Role = get(ctx.author.guild.roles, name=str(HeBotRole.VerificationPending))

        verified: bool = role_verified in ctx.author.roles
        pending: bool = role_pending in ctx.author.roles

        response: Embed
        if verified:
            # Persistence:
            server: Server = Persistence.get_server(str(ctx.guild.id))
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
                )
            )
        elif pending:
            response = ErrorEmbed(
                error_type=ErrorType.Permission,
                source=ctx.command.name,
                reason=(
                    f"{ctx.author.mention} "
                    f"You must wait for your verification process to finish, before you can unverify."
                )
            )
        else:
            response = ErrorEmbed(
                error_type=ErrorType.Permission,
                source=ctx.command.name,
                reason=(
                    f"{ctx.author.mention} "
                    f"You must be verified before you can be unverified!"
                )
            )

        await ctx.respond(embed=response)

    bot.run(EnvVars["discord_bot_token"])


if __name__ == '__main__':
    main()
