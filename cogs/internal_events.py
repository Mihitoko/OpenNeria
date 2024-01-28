import asyncio
import logging
import time

import discord
from discord import Interaction, Forbidden, DiscordException
from discord.app_commands import CommandInvokeError
from discord.ext import commands

from errors.error_handler import ErrorStringHandler
from locales.gen import get_language, LanguageSchema

import errors.basic
from bot import Neria
from persistence.models import Server
from errors import registration
from utils.config_manager import ConfigManager
from utils.context_interace import ContextInterface
from utils.overwrites import BetterEmbed
from errors.basic import ModalInteractionCallbackError, NumberConversionError, DateConversionError, NotAPreset, \
    DateTimeInPast, InvalidNumber, EventNotFound, NotAManager

logger = logging.getLogger("Neria")


class InternalEventsCog(commands.cog.Cog):
    def __init__(self, bot: Neria):
        super(InternalEventsCog, self).__init__()
        self.bot = bot
        self.err_handler = ErrorStringHandler()

    @commands.Cog.listener()
    async def on_ui_error(self, interaction: Interaction, error: Exception):
        self.bot.dispatch("handle_error", ContextInterface(interaction), error)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        pass

    @commands.Cog.listener()
    async def on_handle_error(self, context: ContextInterface, exception: DiscordException) -> None:
        embed = BetterEmbed(BetterEmbed.ERROR)
        embed.set_default_thumbnail()
        embed.footer_from_interaction(context.interaction)
        if not context.guild and context.interaction.command:
            lang: LanguageSchema.Errors.guild_only = get_language("en", LanguageSchema.Errors.guild_only)
            embed.set_header(lang.title.get_string())
            embed.description = lang.desc.get_string()
            await context.entity.response.send_message(embed=embed)
            return
        logger.debug(f"Errorhandler called for command {context.command_name} in server {context.guild.id}")
        server = await Server.get_safe(context.guild.id)
        lang: LanguageSchema.Errors = get_language(server.lang, LanguageSchema.Errors)
        interaction = context.interaction
        real_exc = exception
        x = self.bot.interaction_income_mapping.pop(context.interaction.id, None)
        if isinstance(exception, CommandInvokeError):
            if isinstance(exception.original, ModalInteractionCallbackError):
                interaction = exception.original.interaction
                real_exc = exception.original.real_exception
            else:
                real_exc = exception.original

        if isinstance(exception, ModalInteractionCallbackError):
            interaction = exception.interaction
            real_exc = exception.real_exception

        err_text = self.err_handler.get_err_text(lang, real_exc, interaction)
        if err_text is not None:
            embed.set_header(err_text[0])
            embed.description = err_text[1]

        if err_text is None:
            if x:
                t = round(time.time() - x, 3)
            else:
                t = "Not found"
            logger.error(f"Unhandled error in command {context.command_name} invoked in server {context.guild.id} "
                         f"(took {t} seconds)",
                         exc_info=real_exc)
            error_ch_id = ConfigManager.get_setting("error_ch")
            error_channel = self.bot.get_channel(error_ch_id)
            emb = BetterEmbed(BetterEmbed.ERROR)
            emb.set_header("Unhanded error Report")
            emb.description = lang.default.report.get_string(interaction.guild.id, interaction.guild.name,
                                                             interaction.user.id,
                                                             interaction.user.name, str(t), real_exc)
            if not self.bot.is_debug():
                await error_channel.send(embed=emb)
            embed.set_header(lang.default.title.get_string())
            embed.description = lang.default.desc.get_string("https://discord.gg/7q2aGpYQxS")

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                try:
                    await interaction.followup.send(embed=embed, ephemeral=True)
                except DiscordException:
                    await interaction.followup.send(embed=embed, ephemeral=True)
        except DiscordException:
            await context.channel.send(embed=embed)


async def setup(bot: Neria):
    await bot.add_cog(InternalEventsCog(bot))
