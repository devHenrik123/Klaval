from discord import TextChannel, Interaction, ButtonStyle, Button, SelectOption
from discord.abc import GuildChannel
from discord.ext.commands import Context
from discord.ui import button, Modal, InputText, View

from crawler import Team
from dscrd_bot.embeds import DefaultEmbed, OkayEmbed, ErrorEmbed, ErrorType
from dscrd_bot.persistent_data import Server, Persistence, Channel, TeamEvent, TeamLink, TeamLinkSettings
from dscrd_bot.roles import HeBotRole
from dscrd_bot.ui.select_with_callback import SelectWithCallback
from dscrd_bot.ui.views.select_channel_view import SelectChannelView
from dscrd_bot.util import get_crawler


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
            title="Message Style Settings"
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
    await link_team(interaction)


class TryLinkTeamAgainView(View):
    @button(label="Retry")
    async def button_configure_callback(self, _: Button, interaction: Interaction) -> None:
        await link_team(interaction)


class LinkTeamModal(Modal):
    def __init__(self):
        super().__init__(
            title="Link Team"
        )

        self._team_tag: InputText = InputText(
            label="Tag of your Klavia team",
            placeholder="##",
            required=True
        )
        self.add_item(self._team_tag)

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        tag: str = self._team_tag.value.strip()
        try:
            team: Team = get_crawler().get_team(tag)
        except AttributeError:
            await interaction.respond(
                embed=ErrorEmbed(
                    error_type=ErrorType.Parameter,
                    source="Link Team Modal",
                    reason=(
                        f"{interaction.user.mention} "
                        f"Could not find a team with the tag **\"{tag}\"**. "
                        f"Please try again."
                    )
                ),
                view=TryLinkTeamAgainView(),
                ephemeral=True
            )
            return
        server: Server = Persistence.get_server(str(interaction.guild.id))
        server.linked_team = TeamLink(
            tag=team.tag,
            settings=TeamLinkSettings(
                notify_events=[]
            ),
            events_channel=None,
            cached_state=None
        )
        await set_event_notification_channel(interaction)


class LinkTeamView(View):
    @button(label="Configure")
    async def button_configure_callback(self, _: Button, interaction: Interaction) -> None:
        await interaction.response.send_modal(LinkTeamModal())

    @button(label="Skip")
    async def button_skip_callback(self, _: Button, interaction: Interaction) -> None:
        await finish_setup(interaction)


async def link_team(interaction: Interaction) -> None:
    await interaction.respond(
        embed=DefaultEmbed(
            title="Setup - Link Team",
            description=(
                f"{interaction.user.mention} "
                f"You have the option to link a Klavia team to your server. This will allow you and your team members "
                f"to receive status updates. Some benefits of linking a team:\n"
                f"- Receive messages when a new member joins the team.\n"
                f"- Receive messages when a member is promoted to a higher role in the team.\n"
                f"- More coming soon!\n\n"
                f"You can also skip this step."
            )
        ),
        view=LinkTeamView(),
        ephemeral=True
    )


async def set_event_notification_channel(interaction: Interaction) -> None:
    await interaction.respond(
        embed=DefaultEmbed(
            title="Setup - Event Notification Channel",
            description=(
                f"{interaction.user.mention} "
                f"Next you can configure a channel for team event messages.\n\n"
                f"Team event messages will be automatically sent, when a certain team related event happens in Klavia. "
                f"The scope of these messages can be configured later on. As an example, team event messages may "
                f"include information regarding the following topics:\n"
                f"- new member\n"
                f"- member left\n"
                f"- promotion\n\n"
                f"You can skip this or select a channel for me to send them to:"
            )
        ),
        view=SelectTeamEventsChannelView(),
        ephemeral=True
    )


async def finish_setup(interaction: Interaction) -> None:
    # save settings:
    Persistence.write()

    # create roles:
    existing_roles: list[str] = [r.name for r in interaction.guild.roles]
    new_roles: list[HeBotRole] = [e for e in HeBotRole if e not in existing_roles]
    for role in new_roles:
        await interaction.guild.create_role(name=role)

    await interaction.respond(
        embed=OkayEmbed(
            title="Setup - Complete!",
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
        await interaction.response.send_modal(SettingsModal())

    @button(label="Skip")
    async def button_callback(self, _: Button, interaction: Interaction) -> None:
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        server: Server = Persistence.get_server(str(interaction.guild.id))
        server.embed_author = ""
        server.embed_icon_url = ""
        await link_team(interaction)


async def on_welcome_channel_selected(interaction: Interaction, channel: GuildChannel | None) -> None:
    if channel is not None:  # set channel:
        server: Server = Persistence.get_server(str(channel.guild.id))
        server.welcome_channel = Channel(id=str(channel.id))

    await interaction.respond(
        embed=DefaultEmbed(
            title="Setup - Message Style",
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


class ConfigureTeamEventsView(View):
    def __init__(self):
        super().__init__()

        self._selection_to_event_mapping: dict[str, tuple[TeamEvent, str]] = {
            "New Member": (
                TeamEvent.NewMember,
                "Sent when a new member joins the team on Klavia."
            ),
            "Member Left": (
                TeamEvent.MemberLeft,
                "Sent when a member leaves the team on Klavia."
            ),
            "Promotion": (
                TeamEvent.Promotion,
                "Sent when a member has been promoted to a higher role, like Agent."
            )
        }

        options: list[SelectOption] = [
            SelectOption(label=k, description=v[1]) for k, v in self._selection_to_event_mapping.items()
        ]
        self._team_events: SelectWithCallback = SelectWithCallback(
            on_select=self.on_team_events_selected,
            options=options,
            min_values=0,
            max_values=len(options)
        )
        self.add_item(self._team_events)

    async def on_team_events_selected(self, interaction: Interaction, selected: list[str]) -> None:
        server: Server = Persistence.get_server(str(interaction.guild.id))
        server.linked_team.settings.notify_events = []
        for option in selected:
            server.linked_team.settings.notify_events.append(self._selection_to_event_mapping[option][0])
        await finish_setup(interaction)


async def on_team_events_channel_selected(interaction: Interaction, channel: GuildChannel) -> None:
    server: Server = Persistence.get_server(str(interaction.guild.id))
    server.linked_team.events_channel = str(channel.id)
    await interaction.respond(
        embed=DefaultEmbed(
            title="Setup - Team Events",
            description=(
                f"{interaction.user.mention} "
                f"Please select all team events that you wish to receive in {channel.mention} from the list below:"
            )
        ),
        view=ConfigureTeamEventsView(),
        ephemeral=True
    )


class SelectTeamEventsChannelView(SelectChannelView):
    def __init__(self):
        super().__init__(callback=on_team_events_channel_selected)

    @button(label="Skip")
    async def button_callback(self, _: Button, interaction: Interaction) -> None:
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        server: Server = Persistence.get_server(str(interaction.guild.id))
        server.linked_team.events_channel = None
        await finish_setup(interaction)


async def command_setup(ctx: Context) -> None:
    await ctx.response.defer(ephemeral=True)

    # create setup with default values:
    save_setup(ctx.guild.id)

    await ctx.respond(
        embed=DefaultEmbed(
            title=f"Setup - Welcome Channel",
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
