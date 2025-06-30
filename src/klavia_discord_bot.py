from typing import Any

from discord import Member, Intents, Embed, Bot, Role, Guild
from discord.abc import GuildChannel
from discord.ext import commands, tasks
from discord.ext.commands import Context, CommandError
from discord.utils import get

from dscrd_bot.background_tasks.task_notify_shop_update import task_notify_shop_update
from dscrd_bot.background_tasks.task_notify_team_events import task_notify_team_events
from dscrd_bot.background_tasks.task_persist_shop_state import task_persist_shop_state
from dscrd_bot.background_tasks.task_persist_team_state import task_persist_team_state
from dscrd_bot.background_tasks.task_sync_users import task_sync_users
from dscrd_bot.commands.find_racer import command_find_racer
from dscrd_bot.commands.force_unverify import command_force_unverify
from dscrd_bot.commands.force_verify import command_force_verify
from dscrd_bot.commands.garage import command_garage
from dscrd_bot.commands.quests import command_quests
from dscrd_bot.commands.setup import command_setup
from dscrd_bot.commands.stats import command_stats
from dscrd_bot.commands.sync import command_sync
from dscrd_bot.commands.unverify import command_unverify
from dscrd_bot.commands.verify import command_verify
from dscrd_bot.embeds import DefaultEmbed
from dscrd_bot.roles import HeBotRole
from dscrd_bot.persistent_data import Persistence, Server
from dscrd_bot.util import is_verified, error_handler, EnvVars, BotName


def main() -> None:
    intents: Intents = Intents(
        guilds=True,
        messages=True,
        message_content=True,
        members=True
    )

    if EnvVars["operation_mode"] == "development":
        bot: Bot = Bot(
            intents=intents,
            sync_commands=False,
            auto_sync_commands=False,
            default_guild_ids=[int(EnvVars["dev_server_id"])]
        )
    else:
        bot: Bot = Bot(intents=intents)

    # noinspection PyBroadException
    @tasks.loop(hours=.5)
    async def scheduled_trigger() -> Any:
        try:
            print("Start scheduled trigger.")

            try:
                print("Sync users . . .")
                await task_sync_users(bot)
            except Exception as ex:
                pass  # keep it running...
                print("Error during user synchronization: ", ex)

            try:
                print("Process team events . . .")
                await task_notify_team_events(bot)
            except Exception as ex:
                pass  # keep it running...
                print("Error during team event processing: ", ex)

            try:
                print("Persist team state . . .")
                await task_persist_team_state()
            except Exception as ex:
                pass  # keep it running...
                print("Error during persistence update: ", ex)

            try:
                print("Send shop updates . . .")
                await task_notify_shop_update(bot)
                print("Persist shop state . . .")
                await task_persist_shop_state()
            except Exception as ex:
                pass  # keep it running...
                print("Ecountered an error during shop notify or persist: ", ex)

        except Exception as ex:
            pass  # I don't know what might have happend, but rather broad exception than crashing.
            print("Scheduled trigger failed: ", ex)
        finally:
            print("Scheduled trigger finished.")

    @bot.event
    async def on_ready() -> Any:
        scheduled_trigger.start()

    @bot.event
    async def on_guild_join(guild: Guild) -> Any:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    embed=DefaultEmbed(
                        title=f"Hello, I am {BotName}.",
                        description=(
                            "Thank you for adding me to your server! To make sure that I can do my work properly, please "
                            "move my role to the top of the roles list. To configure me, use the **/setup** command. "
                            "If you are interested in the source code, you may take a look at the official "
                            f"[{BotName}](https://github.com/devHenrik123/Klaval) "
                            "git repository. If you want to discover useful commands and features, please take a look "
                            " at the [readme file](https://github.com/devHenrik123/Klaval/blob/main/README.md)."
                        )
                    )
                )
                break

    @bot.event
    async def on_member_join(member: Member) -> Any:
        server: Server = Persistence.get_server(str(member.guild.id))
        if server.welcome_channel is not None:
            welcome_channel: GuildChannel = bot.get_channel(int(server.welcome_channel.id))
            role_unverified: Role = get(member.guild.roles, name=HeBotRole.Unverified)
            await member.add_roles(role_unverified)
            embed: Embed = DefaultEmbed(
                f"Welcome {member.display_name}!",
                description=(
                    f"{member.mention} Please verify your Klavia account to gain access to all channels.\n"
                    f"To do so, use the **/verify** command. "
                ),
                custom_title=server.embed_author,
                author_icon_url=server.embed_icon_url
            )
            await welcome_channel.send("", embed=embed)

    @bot.event
    async def on_member_remove(member: Member) -> Any:
        server: Server = Persistence.get_server(str(member.guild.id))
        if is_verified(member):
            # Remove member from persistence:
            server.verified_users = [u for u in server.verified_users if u.id != str(member.id)]
            Persistence.write()
        if server.welcome_channel is not None:
            await bot.get_channel(int(server.welcome_channel.id)).send(
                embed=DefaultEmbed(
                    title="User Left",
                    description=(
                        f"{member.mention} has left the server."
                    ),
                    custom_title=server.embed_author,
                    author_icon_url=server.embed_icon_url
                )
            )

    @commands.has_permissions(administrator=True)
    @bot.slash_command(description="Force a user verification. Can only be used by admins.")
    async def force_verify(ctx: Context, user: Member, klavia_id: str) -> Any:
        await command_force_verify(ctx, user, klavia_id)

    @force_verify.error
    async def force_verify_error(ctx: Context, error: CommandError) -> Any:
        await error_handler(ctx, error)

    @commands.has_permissions(administrator=True)
    @bot.slash_command(description="Admins can use this to configure Klavals behavior.")
    async def setup(ctx: Context) -> Any:
        await command_setup(ctx)

    @setup.error
    async def setup_error(ctx: Context, error: CommandError) -> Any:
        await error_handler(ctx, error)

    @bot.slash_command(description="Show a users current quests.")
    async def quests(ctx: Context, klavia_name: str = "") -> Any:
        await command_quests(ctx, klavia_name)

    @bot.slash_command(description="Show a users stats.")
    async def stats(ctx: Context, klavia_name: str = "") -> Any:
        await command_stats(ctx, klavia_name)

    @bot.slash_command(description="Show a users garage.")
    async def garage(ctx: Context, klavia_name: str = "") -> Any:
        await command_garage(ctx, klavia_name)

    @bot.slash_command(description="Verify your account by linking it to your Klavia profile.")
    async def verify(ctx: Context, klavia_name: str) -> Any:
        await command_verify(ctx, klavia_name)

    @bot.slash_command(description="Synchronize your Discord profile with your Klavia account.")
    async def sync(ctx: Context) -> Any:
        await command_sync(ctx)

    @commands.has_permissions(administrator=True)
    @bot.slash_command(description="Force unverify a user.")
    async def force_unverify(ctx: Context, user: Member) -> Any:
        await command_force_unverify(ctx, user)

    @force_unverify.error
    async def force_unverify_error(ctx: Context, error: CommandError) -> Any:
        await error_handler(ctx, error)


    @bot.slash_command(description="Unlink your Klavia account from your Discord profile.")
    async def unverify(ctx: Context) -> Any:
        await command_unverify(ctx)

    @bot.slash_command(description="Finds all matching Klavia accounts.")
    async def find_racer(ctx: Context, klavia_name: str) -> Any:
        await command_find_racer(ctx, klavia_name)

    bot.run(EnvVars["discord_bot_token"])


if __name__ == '__main__':
    main()
