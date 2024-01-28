import asyncio

import discord.ui
from discord import Interaction
from locales.gen import get_language, LanguageSchema

from errors.basic import ModalInteractionCallbackError
from ui.modals.input_fields import ModalInputBase


class AwaitableModal(discord.ui.Modal):

    def __init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        super(AwaitableModal, self).__init__(*args, **kwargs)
        self.future = loop.create_future()
        self.prepare_modal()

    async def wait_result(self, timeout):
        try:
            return await asyncio.wait_for(self.future, timeout=timeout)
        finally:
            self.stop()

    async def on_submit(self, interaction: Interaction) -> None:
        """
        Pass on_submit instant to :meth: callback to make the migration to discord.py easier
        :param interaction:
        :return:
        """
        await self.callback(interaction)

    async def callback(self, interaction: Interaction):
        raise NotImplementedError

    async def get_result(self, timeout=60):
        raise NotImplementedError

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        to_return = ModalInteractionCallbackError(error, interaction)
        self.future.set_exception(to_return)

    def prepare_modal(self):
        raise NotImplementedError


class BaseModal(AwaitableModal):

    def __init__(self, *args, **kwargs):
        self.to_set: list[ModalInputBase] = []
        self.lang_raw = kwargs.pop("lang", "en")
        self.language: LanguageSchema.modals = get_language(self.lang_raw).modals
        super().__init__(asyncio.get_running_loop(), *args, **kwargs)

    async def callback(self, interaction: Interaction):
        ret_dict = {item.entity_name: item.convert() for item in self.to_set}
        self.future.set_result((interaction, ret_dict))

    async def get_result(self, timeout=60):
        raise NotImplementedError

    def get_items(self):
        raise NotImplementedError

    def prepare_modal(self):
        items = self.get_items()
        for i in items:
            self.add_item(
                i
            )
            self.to_set.append(i)


