import discord

from ui.modals.modal_base import BaseModal


class DynamicModal(BaseModal):
    def __init__(self, items, *args, **kwargs):
        self.items = items
        super().__init__(*args, **kwargs)

    async def get_result(self, timeout=60) -> tuple[discord.Interaction, dict]:
        return await self.wait_result(timeout)

    def get_items(self):
        return self.items
