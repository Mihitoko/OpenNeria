import asyncio

from discord import Interaction
from discord.app_commands import CommandTree, AppCommandError

from utils.context_interace import ContextInterface


class ApplicationCommandTree(CommandTree):
    async def on_error(self, interaction: Interaction, error: AppCommandError) -> None:
        interface = ContextInterface(interaction)
        self.client.dispatch("handle_error", interface, error)

    async def call(self, interaction: Interaction) -> None:
        loop = asyncio.get_running_loop()
        await super().call(interaction)

