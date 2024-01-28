import asyncio

import discord
from discord import ButtonStyle, Interaction

from utils.overwrites import FixedView


class ProceedView(FixedView):
    def __init__(self, user_id):
        super().__init__(timeout=500)
        self.user_id = user_id
        loop = asyncio.get_running_loop()
        self.future = loop.create_future()

    @discord.ui.button(label="Proceed", style=ButtonStyle.blurple)
    async def pressed(self, interaction, item):

        self.future.set_result(interaction)

    async def wait_for_press(self):
        return await self.future

    async def on_timeout(self) -> None:
        self.future.cancel()

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
