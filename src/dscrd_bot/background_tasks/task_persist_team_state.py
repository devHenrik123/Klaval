from crawler import Team, UserIdentity
from dscrd_bot.persistent_data import Persistence, CachedTeamMember, CachedTeamState, TeamMemberRole
from dscrd_bot.util import get_crawler


class TeamMemberRoleMapper:
    def __init__(self, team: Team) -> None:
        self._mapping: dict[str, TeamMemberRole] = {
            team.leader.id: TeamMemberRole.Leader,
        } | {agent.id: TeamMemberRole.Agent for agent in team.agents}

    def get(self, team_member: UserIdentity) -> TeamMemberRole:
        return self._mapping.get(team_member.id, TeamMemberRole.Regular)


async def task_persist_team_state() -> None:
    for server in Persistence.get().servers:
        if server.linked_team:
            team: Team = get_crawler().get_team(server.linked_team.tag)
            if not server.linked_team.cached_state:
                server.linked_team.cached_state = CachedTeamState(members=[])
            role_mapper: TeamMemberRoleMapper = TeamMemberRoleMapper(team)
            server.linked_team.cached_state.members = [
                CachedTeamMember(
                    id=m.id,
                    role=role_mapper.get(m)
                )
                for m in team.members
            ]
    Persistence.write()
