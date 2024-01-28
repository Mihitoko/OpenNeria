import asyncio
import logging
import socket
import time

import aiohttp
import discord
from discord.ext.commands import Cog
from discord import Embed, Interaction
from discord.ui import Item
from discord.webhook.async_ import AsyncWebhookAdapter, AsyncDeferredLock

from locales.gen import get_language
from utils.media_manager import MediaManager
from utils.utils import TimingContext

logger = logging.getLogger("Neria.webhook_watcher")
#  Overwrite to narrow down why some interactions fail.
old_sender = AsyncWebhookAdapter.request


async def timed_webhook_request(*args, **kwargs):
    with TimingContext("async_webhook_request", max_time=3):
        return await old_sender(*args, **kwargs)


AsyncWebhookAdapter.request = timed_webhook_request


class ExtDeferredLock(AsyncDeferredLock):

    def __init__(self, lock: asyncio.Lock):
        super().__init__(lock)
        self.in_time = time.time()

    async def __aenter__(self):
        ret = await super(ExtDeferredLock, self).__aenter__()
        if time.time() - self.in_time > 2:
            logger.warning("Lock took more then 2 seconds")
        logger.debug("Webhook lock enter")
        return ret

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.delta:
            logger.warning(f"Delta is set to {self.delta}")
        await super(ExtDeferredLock, self).__aexit__(exc_type, exc_val, exc_tb)
        if time.time() - self.in_time > 3:
            logger.warning("Webhook took more then 3 seconds")
        logger.debug("Webhook exit")


discord.webhook.async_.AsyncDeferredLock = ExtDeferredLock


class ExtCog(Cog):

    def get_lang(self, lang: str):
        raise NotImplementedError

    def get_lang_by_reference(self, lang: str, reference: type):
        return get_language(lang, reference)


class LangAvailable:
    def get_lang(self, lang: str):
        raise NotImplementedError

    def get_lang_by_reference(self, lang: str, reference: type):
        return get_language(lang, reference)


class BetterEmbed(Embed):
    DEFAULT = "default"
    INFO = "info"
    ERROR = "error"
    OK = "ok"

    def __init__(self, embed_type="default", **kwargs):
        super(BetterEmbed, self).__init__(**kwargs)
        self.embed_type = embed_type
        self.initiate()

    @property
    def assets(self):
        return MediaManager.get_icon(self.embed_type)

    def change_type(self, t, change_thump=True):
        self.embed_type = t
        if self.author is None:
            t = ""
        else:
            t = self.author.name
        self.set_header(t)
        self.initiate()
        if change_thump:
            self.set_default_thumbnail()

    def set_color(self):
        self.color = MediaManager.get_color(self.embed_type)

    def set_header(self, text: str):
        self.set_author(name=text, icon_url=self.assets)

    def initiate(self):
        self.set_color()

    def set_default_thumbnail(self):
        self.set_thumbnail(url=MediaManager.get_thumbnail_rand())

    def footer_from_interaction(self, interaction: Interaction):
        a: discord.Member = interaction.user
        self.set_footer(icon_url=a.avatar.url if a.avatar else a.default_avatar.url,
                        text=f"{a.name} | Neria | {interaction.client.ver}")  # noqa


class FixedView(discord.ui.View):
    """
    Alias for discord.ui.View
    """


def hook_type(to_hook, new_cls: type):
    if to_hook not in new_cls.__mro__:
        raise TypeError(f"{new_cls} musst subclass {to_hook}")
    old_new = to_hook.__new__

    def hook(_, *args, **kwargs) -> type:
        if hasattr(old_new, "__self__"):
            if old_new.__self__ is object:
                return old_new(new_cls)
        return old_new(new_cls, *args, **kwargs)

    to_hook.__new__ = hook


class HookedTCPConnector(aiohttp.TCPConnector):
    def __init__(self, *args, **kwargs):
        kwargs.update({"family": socket.AF_INET})
        super().__init__(*args, **kwargs)


hook_type(aiohttp.TCPConnector, HookedTCPConnector)
