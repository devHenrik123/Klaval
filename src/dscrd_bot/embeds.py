from enum import StrEnum
from typing import Final, override, cast

from discord import Embed, Colour
from discord.embeds import E, EmbedField


class ErrorType(StrEnum):
    Permission = "Permission Error"
    Timeout = "Timeout Error"
    Parameter = "Invalid Parameter"


class DefaultEmbed(Embed):
    KlaviaIcon: Final[str] = "https://klavia.io/assets/klavia_season_1-36be9a740f9c08419bb280628ec0c6f4d5bf419c1617da02ac8e91aa86367bf5.png"
    TeamIcon: Final[str] = "https://cdn.discordapp.com/icons/1282935249298522122/40ea0effd154282afb36795a420bb468.png"

    def __init__(self, title: str, description: str = "", *args, **kwargs) -> None:
        super().__init__(
            title=title,
            description=description,
            color=Colour.blurple(),
            *args,
            **kwargs
        )
        # self._add_custom_footer()
        self.set_author(name="[MV] Marvel", icon_url=DefaultEmbed.TeamIcon)
        self.set_footer(text="Bot made by Henrik.", icon_url=DefaultEmbed.KlaviaIcon)

    # Issue: Custom footer is inserted above images...
    """def _add_custom_footer(self) -> None:
        super().add_field(name="", value="[Source Code](https://google.com)", inline=False)

    @override
    def add_field(self: E, *, name: str = "", value: str = "", inline: bool = True) -> Embed:
        field_count: int = len(cast(list[EmbedField], self.fields))
        self._add_custom_footer()
        self.set_field_at(
            index=field_count - 1,
            name=name,
            value=value,
            inline=inline
        )
        return self"""


class ErrorEmbed(DefaultEmbed):
    def __init__(self, error_type: ErrorType, source: str, reason: str) -> None:
        super().__init__(
            title=error_type,
            description=f"Source: {source}\nReason: {reason}"
        )
        self.colour = Colour.red()


class OkayEmbed(DefaultEmbed):
    def __init__(self, title: str, description: str = "") -> None:
        super().__init__(
            title=title,
            description=description
        )
        self.colour = Colour.green()
