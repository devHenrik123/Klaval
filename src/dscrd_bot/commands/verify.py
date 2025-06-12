from asyncio import sleep
from random import choice
from time import time
from typing import Any, Final

from discord import Role, Interaction
from discord.ext.commands import Context
from discord.utils import get

from crawler import Garage, Car, UserIdentity
from dscrd_bot.embeds import DefaultEmbed, OkayEmbed, ErrorType, ErrorEmbed
from dscrd_bot.roles import HeBotRole
from dscrd_bot.persistent_data import Persistence, Server, User
from dscrd_bot.ui.views.select_user_view import SelectUserView
from dscrd_bot.util import get_crawler


VerificationPollingRate: Final[int] = 30  # check for verification every <polling_rate> seconds
VerificationTimeout: Final[int] = 60 * 5  # verification timeout in seconds


async def on_account_selected(interaction: Interaction, identity: UserIdentity) -> None:
    role_verified: Role = get(interaction.guild.roles, name=str(HeBotRole.Verified))
    role_unverified: Role = get(interaction.guild.roles, name=str(HeBotRole.Unverified))
    role_pending: Role = get(interaction.guild.roles, name=str(HeBotRole.VerificationPending))

    server: Server = Persistence.get_server(str(interaction.guild.id))
    garage: Garage = get_crawler().get_garage(identity.id)

    if len(garage.cars) <= 1:
        await interaction.respond(
            embed=ErrorEmbed(
                error_type=ErrorType.Permission,
                source=interaction.data.get("name"),
                reason=f"You must own at least two cars to get verified. You currently own {len(garage.cars)}.",
                custom_title=server.embed_author,
                author_icon_url=server.embed_icon_url
            ),
            ephemeral=True
        )
        return

    initial_car: Car = garage.selected_car
    random_car: Car = choice([c for c in garage.cars if c.name != initial_car.name])

    await interaction.respond(
        embed=DefaultEmbed(
            title="Verification",
            description=(
                f"{interaction.user.mention} "
                f"To verify your account, please change your selected car in Klavia to **{random_car.name}**.\n"
                f"Verification will take a minimum of {VerificationPollingRate} seconds."
            ),
            custom_title=server.embed_author,
            author_icon_url=server.embed_icon_url,
            image=random_car.image_url
        ),
        ephemeral=True
    )
    await interaction.user.add_roles(role_pending)

    start_time: float = time()
    timed_out: bool = False
    verified: bool = False
    while not verified and not timed_out:
        await sleep(VerificationPollingRate)
        car: Car = get_crawler().get_garage(identity.id).selected_car

        if car.name == random_car.name:
            verified = True

            # Persistence:
            server: Server = Persistence.get_server(str(interaction.guild.id))
            server.verified_users.append(
                User(
                    id=str(interaction.user.id),
                    klavia_id=identity.id
                )
            )
            Persistence.write()

            # Roles:
            await interaction.user.remove_roles(role_unverified)
            await interaction.user.add_roles(role_verified)
            if interaction.user != interaction.guild.owner:
                # Cannot edit owner profile through bots.
                await interaction.user.edit(nick=get_crawler().get_garage(identity.id).display_name)

        timed_out = time() >= start_time + VerificationTimeout

    await interaction.user.remove_roles(role_pending)

    if verified:
        await interaction.respond(
            embed=OkayEmbed(
                title="Verified",
                description=(
                    f"{interaction.user.mention} "
                    f"You have been verified. You may now change your selected car to whatever you like."
                ),
                custom_title=server.embed_author,
                author_icon_url=server.embed_icon_url
            ),
            ephemeral=True
        )
    else:
        await interaction.respond(
            embed=ErrorEmbed(
                error_type=ErrorType.Timeout,
                source=interaction.data.get("name"),
                reason=(
                    f"{interaction.user.mention}"
                    f"Cannot verify your account.\n"
                    f"Please try again later."
                ),
                custom_title=server.embed_author,
                author_icon_url=server.embed_icon_url
            ),
            ephemeral=True
        )


async def command_verify(ctx: Context, klavia_name: str) -> Any:
    await ctx.response.defer(ephemeral=True)

    server: Server = Persistence.get_server(str(ctx.guild.id))

    role_verified: Role = get(ctx.author.guild.roles, name=str(HeBotRole.Verified))
    role_pending: Role = get(ctx.author.guild.roles, name=str(HeBotRole.VerificationPending))

    verified: bool = role_verified in ctx.author.roles
    pending: bool = role_pending in ctx.author.roles

    if verified:
        await ctx.respond(
            embed=DefaultEmbed(
                title="Verified",
                description="You have already been verified.",
                custom_title=server.embed_author,
                author_icon_url=server.embed_icon_url
            ),
            ephemeral=True
        )
    elif pending:
        await ctx.respond(
            embed=DefaultEmbed(
                title="Pending Verification",
                description=(
                    f"{ctx.author.mention} "
                    f"You are currently being verified. Please be patient.\n"
                    f"Verification will take a minimum of {VerificationPollingRate} seconds."
                ),
                custom_title=server.embed_author,
                author_icon_url=server.embed_icon_url
            ),
            ephemeral=True
        )
    elif not verified:
        possible_identities: list[UserIdentity] = get_crawler().search_racers(klavia_name)
        if len(possible_identities) >= 25:
            possible_identities = possible_identities[:25]

        await ctx.respond(
            embed=DefaultEmbed(
                title="Verification",
                description=(
                    f"{ctx.author.mention} "
                    f"Please select your Klavia account from the list below:"
                ),
                custom_title=server.embed_author,
                author_icon_url=server.embed_icon_url,
            ),
            view=SelectUserView(
                possible_identities,
                on_account_selected
            ),
            ephemeral=True
        )
