from discord.ext.commands import Context

from crawler import Team
from dscrd_bot.embeds import OkayEmbed
from dscrd_bot.persistent_data import Persistence, Server, TeamLink, TeamLinkSettings
from dscrd_bot.util import get_crawler, verification_check_passed


async def command_link_team(ctx: Context, team_tag: str) -> None:
    await ctx.response.defer(ephemeral=True)
    if not await verification_check_passed(ctx):
        return

    team_tag = team_tag.upper()

    server: Server = Persistence.get_server(str(ctx.guild.id))
    team: Team = get_crawler().get_team(team_tag)
    """klavia_account: UserIdentity = get_crawler().search_racer(
        next(u.id for u in server.verified_users if u.id == str(ctx.author.id))
    )"""
    server.linked_team = TeamLink(
        tag=team.tag,
        settings=TeamLinkSettings()
    )
    Persistence.write()
    await ctx.respond(
        embed=OkayEmbed(
            title="Link Team",
            description=(
                f"{ctx.author.mention} "
                f"Successfully linked team **[{team.tag}] {team.name}** to the server."
            )
        ),
        ephemeral=True
    )
