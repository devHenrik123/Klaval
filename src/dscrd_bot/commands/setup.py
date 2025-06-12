from discord import TextChannel, Interaction, ButtonStyle, Button
from discord.abc import GuildChannel
from discord.ext.commands import Context
from discord.ui import button, Modal, InputText, View

from dscrd_bot.embeds import DefaultEmbed, OkayEmbed
from dscrd_bot.persistent_data import Server, Persistence, Channel
from dscrd_bot.roles import HeBotRole
from dscrd_bot.ui.views.select_channel_view import SelectChannelView


def save_setup(
        guild_id: int,
        message_author: str = "",
        message_icon_url: str = "",
        welcome_channel: TextChannel | None = None
) -> None:
    server: Server = Persistence.get_server(str(guild_id))
    if welcome_channel is not None:
        server.welcome_channel = Channel(id=str(welcome_channel.id))
    server.embed_author = message_author
    server.embed_icon_url = message_icon_url
    Persistence.write()


class SettingsModal(Modal):
    def __init__(self) -> None:
        super().__init__(
            title="Settings"
        )

        self._author_name: InputText = InputText(
            label="Your team name",
            placeholder="Team Name",
            required=False
        )
        self.add_item(self._author_name)

        self._author_icon: InputText = InputText(
            label="Your team icon",
            placeholder="Team Icon Url",
            required=False
        )
        self.add_item(self._author_icon)

    async def callback(self, interaction: Interaction) -> None:
        await on_settings_modal_confirmed(interaction, self._author_name.value, self._author_icon.value)


async def on_settings_modal_confirmed(interaction: Interaction, author_name: str, author_icon_url: str) -> None:
    server: Server = Persistence.get_server(str(interaction.guild.id))
    server.embed_author = author_name
    server.embed_icon_url = author_icon_url
    await finish_setup(interaction)


async def finish_setup(interaction: Interaction):
    # save settings:
    Persistence.write()

    # create roles:
    existing_roles: list[str] = [r.name for r in interaction.guild.roles]
    new_roles: list[HeBotRole] = [e for e in HeBotRole if e not in existing_roles]
    for role in new_roles:
        await interaction.guild.create_role(name=role)

    await interaction.respond(
        embed=OkayEmbed(
            title="Setup",
            description=(
                f"{interaction.user.mention} "
                f"Thank you very much! The setup has been completed! In case you wish to change anything, just run "
                f"the *setup* command again."
            )
        ),
        ephemeral=True
    )


class StartSettingsModalView(View):
    @button(label="Configure")
    async def button_one_callback(self, _: Button, interaction: Interaction) -> None:
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        await interaction.response.send_modal(SettingsModal())

    @button(label="Skip")
    async def button_callback(self, _: Button, interaction: Interaction) -> None:
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        server: Server = Persistence.get_server(str(interaction.guild.id))
        server.embed_author = ""
        server.embed_icon_url = ""
        await finish_setup(interaction)


async def on_welcome_channel_selected(interaction: Interaction, channel: GuildChannel | None) -> None:
    if channel is not None:  # set channel:
        server: Server = Persistence.get_server(str(channel.guild.id))
        server.welcome_channel = Channel(id=str(channel.id))

    await interaction.respond(
        embed=DefaultEmbed(
            title="Setup",
            description=(
                f"{interaction.user.mention} "
                f"{f'I have set the welcome channel to {channel.mention}.\n' if channel is not None else ''}"
                f"Would you like to set a team name and icon url? I will always prepend these to any "
                f"message that I send. You can also skip this step."
            )
        ),
        view=StartSettingsModalView(),
        ephemeral=True
    )


class SelectWelcomeChannelView(SelectChannelView):
    def __init__(self):
        super().__init__(callback=on_welcome_channel_selected)

    @button(label="Skip")
    async def button_callback(self, _: Button, interaction: Interaction) -> None:
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        await on_welcome_channel_selected(interaction, None)


async def command_setup(ctx: Context) -> None:
    await ctx.response.defer(ephemeral=True)

    # create setup with default values:
    save_setup(ctx.guild.id)

    await ctx.respond(
        embed=DefaultEmbed(
            title=f"Setup",
            description=(
                f"{ctx.author.mention} "
                f"The setup has been restored to default settings. "
                f"I will now guide you through the setup procedure.\n\n"
                f"Please select a welcome channel. This will be the place where I will welcome "
                f"new team members and ask them to verify and link their Klavia account. "
                f"You can skip this step, if you prefer that I do not greet new members."
            )
        ),
        view=SelectWelcomeChannelView(),
        ephemeral=True
    )
