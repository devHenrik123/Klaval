from discord import Embed
from discord.ext.commands import Context

from crawler import Garage, Car
from dscrd_bot.embeds import DefaultEmbed
from dscrd_bot.persistent_data import Persistence, Server
from dscrd_bot.util import verification_check_passed, get_crawler, get_klavia_id_by_name, BlankLine


async def command_garage(ctx: Context, klavia_name: str = "") -> None:
    await ctx.response.defer()
    server: Server = Persistence.get_server(str(ctx.guild.id))

    if not await verification_check_passed(ctx):
        return

    klavia_id: str | None = await get_klavia_id_by_name(ctx, klavia_name)
    if klavia_id is None:
        return

    garage_data: Garage = get_crawler().get_garage(klavia_id)

    def cars(cols: int) -> list[list[Car]]:
        output: list[list[Car]] = [[] for _ in range(cols)]
        for i, car in enumerate(garage_data.cars):
            output[i % cols].append(car)
        return output

    response: Embed = DefaultEmbed(
        title=f"{garage_data.display_name}'s Garage:",
        description="".join([
            BlankLine,
            f"**Owned cars:** {len(garage_data.cars)}\n"
        ]),
        thumbnail=garage_data.selected_car.image_url,
        image=garage_data.selected_car.image_url,
        custom_title=server.embed_author,
        author_icon_url=server.embed_icon_url
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
