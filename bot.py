import asyncio
import logging
import os
import time
import typing

import discord
from discord import AllowedMentions
from discord.ext.commands import AutoShardedBot

from command_tree import ApplicationCommandTree
from ui.views.persistant import LFGPingViewPersistent, LFGRegisterViewPersistent
from utils.config_manager import ConfigManager
from utils.media_manager import MediaManager
from utils.utils import scan_cogs

if typing.TYPE_CHECKING:
    from cogs.events import EventCog
    from cogs.scheduler import ScheduleManager
    from cogs.stats import StatManagement

logger = logging.getLogger("Neria")


class Neria(AutoShardedBot):
    def __init__(self):
        intents: discord.Intents = discord.Intents.none()
        # No PyCharm... its not read only..........
        intents.members = True  # noqa
        intents.guilds = True  # noqa
        intents.emojis = True  # noqa
        intents.guild_messages = True  # noqa
        super().__init__(
            command_prefix="",
            help_command=None,
            intents=intents,
            allowed_mentions=AllowedMentions.all().all(),
            tree_cls=ApplicationCommandTree
        )

        self.interaction_income_mapping = {}

    async def on_message(self, message: discord.Message, /) -> None:
        """
        Do not allow normal commands to be dispatched
        :param message:
        :return:
        """
        return

    async def setup_hook(self) -> None:
        await self.load_extensions()
        self.loop.create_task(self.update_emojis())
        self.loop.create_task(self.update_emoji_icons())
        self.loop.create_task(self.register_persistent())
        if self.is_debug():
            self.tree.copy_global_to(guild=discord.Object(532305660369567745))
            await self.tree.sync(guild=discord.Object(532305660369567745))
        else:
            await self.tree.sync()

    @property
    def ver(self):
        return ConfigManager.get_setting("version")

    @property
    def event_manager(self) -> "EventCog":
        return self.get_cog("EventCog")  # type: Ignore

    @property
    def scheduler(self) -> "ScheduleManager":
        return self.get_cog("ScheduleManager")  # type: Ignore

    @property
    def stat_manager(self) -> "StatManagement":
        return self.get_cog("StatManagement")  # type: Ignore

    def is_debug(self):
        return ConfigManager.get_setting("debug")

    async def load_extensions(self):
        await self.load_extension("cogs.scheduler")
        for cog in scan_cogs():
            try:
                await self.load_extension(cog)
            except discord.ext.commands.ExtensionAlreadyLoaded:
                pass

    async def on_ready(self):
        logger.info(f"Logged in as {self.user.name}. Active on {len(self.guilds)} servers.")

    async def register_persistent(self):
        await self.wait_until_ready()
        self.add_view(
            LFGRegisterViewPersistent(self)
        )
        self.add_view(
            LFGPingViewPersistent(self)
        )

    async def update_emoji_icons(self):
        await self.wait_until_ready()
        logger.info("Updating emoji icons...")
        should_exist = ConfigManager.get_setting("emoji_icons")
        icon_channel_id = ConfigManager.get_setting_default("icon_store_channel", None)
        icon_channel = self.get_channel(icon_channel_id)
        media_icons = MediaManager.get_all()["icons"]
        counter = 0
        t = time.time()
        if icon_channel is None:
            logger.error("Can't update icons because 'icon_channel_store' is not configured or not available.")
            return
        update = []
        for i in should_exist:
            try:
                MediaManager.get_icon(i)
            except KeyError:
                update.append(i)

        for to_update in update:
            entry: os.DirEntry
            for entry in os.scandir("resources/images/emojis"):
                if to_update == entry.name.split(".")[0]:
                    msg = await icon_channel.send(file=discord.File(entry.path))
                    media_icons[to_update] = msg.attachments[0].url
                    counter += 1
        MediaManager.save()
        logger.info(f"Updated {counter} icons. Took {round(time.time() - t, 3)} seconds.")

    async def update_emojis(self):
        emoji_prefix = "neria_"
        counter = 0
        emoji_config = MediaManager.get_all()["emojis"]
        await self.wait_until_ready()
        t = time.time()
        logger.info("Updating emojis...")

        remote_emojis = await self.fetch_application_emojis()
        i: os.DirEntry
        local_emojis = [i for i in os.scandir("resources/images/emojis")]

        if ConfigManager.get_setting_default("force_emoji_update", False):
            logger.warning("Force updating all emojis this should only be active while testing.")
            delete_q = []
            for e in local_emojis:
                remote_emote = discord.utils.get(remote_emojis, name=emoji_prefix + e.name.split(".")[0])
                if remote_emote:
                    delete_q.append(remote_emote.delete())
            if len(delete_q) != 0:
                await asyncio.gather(*delete_q, return_exceptions=True)

            remote_emojis = []
        created_futures = []
        for emoji in local_emojis:
            remote_emote = discord.utils.get(remote_emojis, name=emoji_prefix + emoji.name.split(".")[0])
            if remote_emote is None:
                with open(emoji.path, "rb") as emoji_image:  # rb = Read Binary
                    new_emote = self.create_application_emoji(name=emoji_prefix + emoji.name.split(".")[0],
                                                                 image=emoji_image.read())
                    created_futures.append(new_emote)
                    counter += 1
        if len(created_futures) != 0:
            results = await asyncio.gather(*created_futures)
            for i in results:
                emoji_config[i.name.replace(emoji_prefix, "")] = str(i)
            MediaManager.save()

        logger.info(f"Updated {counter} emojis. Took {round(time.time() - t, 3)} seconds")

    def set_invoke_hook(self, coro):
        self._before_invoke = coro
