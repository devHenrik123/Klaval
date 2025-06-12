from typing import Callable, Coroutine

from discord import SelectOption, Interaction
from discord.ui import View

from crawler import UserIdentity
from dscrd_bot.ui.select_with_callback import SelectWithCallback


class SelectUserView(View):

    def __init__(
            self,
            users: list[UserIdentity],
            callback: Callable[[Interaction, UserIdentity], Coroutine[Interaction, UserIdentity, None]]
    ) -> None:
        super().__init__()
        self._users: list[UserIdentity] = users
        self._callback: Callable[[Interaction, UserIdentity], Coroutine[Interaction, UserIdentity, None]] = callback
        self._select: SelectWithCallback = SelectWithCallback(
            options=[
                SelectOption(
                    label=f"{identity.id} - {identity.display_name} - {identity.username}",
                    value=identity.id
                ) for identity in users
            ],
            placeholder="Klavia Account",
            on_select=self._on_select
        )
        self.add_item(self._select)

    async def _on_select(self, interaction: Interaction, values: list[str]) -> None:
        self._select.disabled = True
        await interaction.response.edit_message(view=self)
        selected: UserIdentity = next(u for u in self._users if u.id == values[0])
        await self._callback(interaction, selected)
