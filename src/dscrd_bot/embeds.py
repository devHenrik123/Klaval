from enum import StrEnum
from random import choice
from typing import Final, override, cast

from discord import Embed, Colour
from discord.embeds import E, EmbedField


class ErrorType(StrEnum):
    Permission = "Permission Error"
    Timeout = "Timeout Error"
    Parameter = "Invalid Parameter"


Quotes: Final[list[str]] = [
    "Thanks to Nusakan!",
    "Klaval was made by Henrik.",
    "Don't forget to race today!",
    "🏎️ Faster is better!",
    "⌨️ Mechanical keyboards. ⌨️",
    "Season 2 is here!",
    "The Boring Car looks most interesting.",
    "What's Rabbit-A-Grow supposed to be?",
    "The Smallmouth Bass is a car.",
    "Anyone's allowed to edit my source code.",
    "Accuracy > Speed"
]


class DefaultEmbed(Embed):
    KlaviaIcon: Final[str] = "https://klavia.io/assets/klavia_season_2-6353a01159273012427268aadeee2db81d48cc1bebfe7bd191cd978a8e7e235e.png"
    # TeamIcon: Final[str] = "https://cdn.discordapp.com/icons/1282935249298522122/40ea0effd154282afb36795a420bb468.png"

    def __init__(self, title: str, description: str = "", custom_title: str = "", author_icon_url: str = "", *args, **kwargs) -> None:
        super().__init__(
            title=title,
            description=description,
            color=Colour.blurple(),
            *args,
            **kwargs
        )
        # self._add_custom_footer()
        self.set_author(name=custom_title, icon_url=author_icon_url)
        self.set_footer(text=choice(Quotes), icon_url=DefaultEmbed.KlaviaIcon)

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
    def __init__(self, error_type: ErrorType, source: str, reason: str, custom_title: str = "", author_icon_url: str = "") -> None:
        super().__init__(
            title=error_type,
            description=f"Source: {source}\nReason: {reason}",
            custom_title=custom_title,
            author_icon_url=author_icon_url
        )
        self.colour = Colour.red()


class OkayEmbed(DefaultEmbed):
    def __init__(self, title: str, description: str = "", custom_title: str = "", author_icon_url: str = "") -> None:
        super().__init__(
            title=title,
            description=description,
            custom_title=custom_title,
            author_icon_url=author_icon_url
        )
        self.colour = Colour.green()
