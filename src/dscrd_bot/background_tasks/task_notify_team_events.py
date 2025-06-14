from asyncio import sleep

from discord import Bot
from discord.abc import GuildChannel

from crawler import Team, UserIdentity, Crawler
from dscrd_bot.embeds import DefaultEmbed
from dscrd_bot.persistent_data import Persistence, CachedTeamState, CachedTeamMember, TeamMemberRole, Server
from dscrd_bot.util import get_crawler


async def notify_promotion(server: Server, channel: GuildChannel, user: UserIdentity) -> None:
    await channel.send(
        embed=DefaultEmbed(
            title="Agent Promotion",
            description=(
                f"**[{user.display_name}]({Crawler.RacerUrl.format(user_id=user.id)})** "
                f"has been promoted to **Agent**!\n\n"
                f"🎆 Congratulations! 🎆"
            ),
            custom_title=server.embed_author,
            author_icon_url=server.embed_icon_url
        )
    )


async def notify_new_member(server: Server, channel: GuildChannel, user: UserIdentity) -> None:
    await channel.send(
        embed=DefaultEmbed(
            title="New Team Member",
            description=(
                f"**[{user.display_name}]({Crawler.RacerUrl.format(user_id=user.id)})** has joined the team."
            ),
            custom_title=server.embed_author,
            author_icon_url=server.embed_icon_url
        )
    )


async def notify_member_left(server: Server, channel: GuildChannel, user: UserIdentity) -> None:
    await channel.send(
        embed=DefaultEmbed(
            title="Member Left",
            description=(
                f"**[{user.display_name}]({Crawler.RacerUrl.format(user_id=user.id)})** has left the team."
            ),
            custom_title=server.embed_author,
            author_icon_url=server.embed_icon_url
        )
    )


async def task_notify_team_events(bot: Bot) -> None:
    for server in Persistence.get().servers:
        if server.linked_team and server.linked_team.cached_state:
            team_events_channel: GuildChannel | None = bot.get_channel(int(server.linked_team.events_channel))
            if not team_events_channel:
                continue  # No channel -> No notification -> can continue to next server

            team: Team = get_crawler().get_team(server.linked_team.tag)
            cache: CachedTeamState = server.linked_team.cached_state

            cached_members: dict[str, CachedTeamMember] = {c.id: c for c in cache.members}
            cached_member_ids: list[str] = list(cached_members.keys())
            current_member_ids: list[str] = [u.id for u in team.members]

            # New members:
            for m in team.members:
                if m.id not in cached_member_ids:
                    await notify_new_member(server, team_events_channel, m)
            await sleep(.5)  # Give bot some time to handle important work.

            # Members left:
            for m_id in cached_member_ids:
                if m_id not in current_member_ids:
                    await notify_member_left(server, team_events_channel, get_crawler().search_racer(m_id))
            await sleep(.5)  # Give bot some time to handle important work.

            # Promotions:
            agent_ids: list[str] = [a.id for a in team.agents]
            for m in team.members:
                if m.id in cached_members:
                    old_state: CachedTeamMember = cached_members[m.id]
                    if old_state.role == TeamMemberRole.Regular and m.id in agent_ids:
                        await notify_promotion(server, team_events_channel, m)
            await sleep(.5)  # Give bot some time to handle important work.
