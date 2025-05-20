import asyncio
from typing import Any

import discord
import discord.utils
from discord import Interaction
from discord.ui import Select

from persistence.models import PlayerCharacter, Event, Server
from utils.media_manager import MediaManager

from utils.overwrites import FixedView
from utils.static import PlayerClass, ClassRepresentation
from utils.utils import get_date_time_str


class SelectView(FixedView):
    def __init__(self, user: discord.User, to_choose: list[Any], **kwargs):
        super().__init__(timeout=kwargs.get("timeout", 60))
        self.user = user
        self.choose_from = to_choose
        self.component = None
        self.future = asyncio.get_running_loop().create_future()
        self.prepare_selection()

    def prepare_selection(self):
        raise NotImplementedError

    async def get_result(self):
        raise NotImplementedError

    async def wait_for_result(self) -> tuple[discord.Interaction, Any]:
        try:
            return await self.future
        finally:
            if not self.is_finished():
                self.stop()

    async def on_timeout(self) -> None:
        self.future.set_exception(asyncio.TimeoutError())


class SetReminderView(SelectView):

    def __init__(self, user, **kwargs):
        choose = [
            300,
            900,
            1800,
            3600
        ]
        self.compare = [
            "5 minutes earlier",
            "15 minutes earlier",
            "30 minutes earlier",
            "1 hour earlier"
        ]
        super(SetReminderView, self).__init__(user, choose, **kwargs)
        self.component.callback = self.selected_callback

    def prepare_selection(self):
        select = Select()
        self.add_item(select)
        for i in self.compare:
            select.add_option(label=i)
        self.component = select

    async def selected_callback(self, interaction: discord.Interaction):
        index = self.compare.index(self.component.values[0])
        self.future.set_result((interaction, self.choose_from[index]))

    async def get_result(self) -> tuple[discord.Interaction, int]:
        return await self.wait_for_result()

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You are not allowed to do this.", ephemeral=True)
            return False
        return True


class CharactersSelectView(SelectView):

    def __init__(self, user: discord.User, to_choose: list[PlayerCharacter]):
        self.compare = []
        to_select = [i for i in to_choose]
        to_select.sort(key=lambda item: item.item_lvl, reverse=True)
        super().__init__(user, to_select)
        self.component.callback = self.selected_callback

    def prepare_selection(self):
        select = Select()
        i: PlayerCharacter
        counter = 1
        for i in self.choose_from:
            s = f"{counter}.) {i.character_name} ({i.character_class.name} | {i.item_lvl} GS)"
            self.compare.append(s)
            select.add_option(emoji=MediaManager.get_emoji(i.character_class.emoji_name),
                              label=s)
            counter += 1
        self.add_item(select)
        self.component = select

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You are not allowed to do this.", ephemeral=True)
            return False
        return True

    async def selected_callback(self, interaction: discord.Interaction):
        selection = self.component.values[0]
        index = self.compare.index(selection)
        self.future.set_result((interaction, self.choose_from[index]))

    async def get_result(self) -> tuple[discord.Interaction, PlayerCharacter]:
        return await self.wait_for_result()


class ClassesSelectView(SelectView):

    def __init__(self, user: discord.User, to_choose: list[ClassRepresentation]):
        super(ClassesSelectView, self).__init__(user, to_choose)
        self.component.callback = self.selected_callback

    def prepare_selection(self):
        select = Select()
        i: PlayerClass  # Type Hint
        for i in self.choose_from:
            select.add_option(emoji=MediaManager.get_emoji(i.emoji_name), label=f"{i.name}")
        self.add_item(select)
        self.component = select

    async def get_result(self):
        return await self.wait_for_result()

    async def selected_callback(self, interaction: discord.Interaction):
        selection = self.component.values[0]
        result = discord.utils.get(self.choose_from, name=selection)
        self.future.set_result((interaction, result))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You are not allowed to do this.", ephemeral=True)
            return False
        return True


class ChooseEventSelect(SelectView):

    def __init__(self, user: discord.User, to_choose: list[Event], server, **kwargs):
        self.compare = []
        self.server: Server = server
        super(ChooseEventSelect, self).__init__(user, to_choose, **kwargs)
        self.component.callback = self.selected_callback

    def prepare_selection(self):
        counter = 1
        i: Event
        select = Select()
        self.add_item(select)
        for i in self.choose_from:
            s = f"{counter}. {i.title} ({get_date_time_str(i.event_start, self.server.time_offset)})"
            self.compare.append(s)
            select.add_option(label=s)
            counter += 1
        self.component = select

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You are not allowed to do this.", ephemeral=True)
            return False
        return True

    async def selected_callback(self, interaction: Interaction):
        selection = self.component.values[0]
        index = self.compare.index(selection)
        self.future.set_result((interaction, self.choose_from[index]))

    async def get_result(self) -> tuple[Interaction, Event]:
        return await self.wait_for_result()


class DynamicSelect(SelectView):

    def __init__(self, user, to_choose, string_map, **kwargs):
        self.string_map: list = string_map
        super(DynamicSelect, self).__init__(user, to_choose, **kwargs)
        self.component.callback = self.selected_callback

    def prepare_selection(self):
        select = Select()
        self.add_item(select)
        for choice in self.string_map:
            select.add_option(label=choice)

        self.component = select

    async def selected_callback(self, interaction: Interaction):
        value = self.component.values[0]
        index = self.string_map.index(value)
        ret = self.choose_from[index]
        self.future.set_result((interaction, ret))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You are not allowed to do this.", ephemeral=True)
            return False
        return True

    async def get_result(self) -> tuple[Interaction, Any]:
        return await self.wait_for_result()
