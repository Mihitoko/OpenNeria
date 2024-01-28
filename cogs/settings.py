import discord
from discord import app_commands
from discord.app_commands import Group

from bot import Neria
from persistence.models import Server
from locales.gen import LanguageSchema

from ui.views import DynamicSelect
from utils.async_checks import has_manager_permission
from utils.config_manager import ConfigManager
from utils.overwrites import ExtCog, BetterEmbed
from utils.static import StaticIdMaps


class ServerManagement(ExtCog):
    group = Group(name="config", description="Manage The server",
                  guild_ids=ConfigManager.get_debug_guild_when_debug())

    def __init__(self, bot: Neria):
        self.bot: Neria = bot

    def get_lang(self, lang: str) -> LanguageSchema.Commands.settings:
        return self.get_lang_by_reference(lang, LanguageSchema.Commands.settings)

    @group.command(description="Select a role that can manage the bot. If not provided role is removed")
    @has_manager_permission()
    async def manager_role(self, interaction: discord.Interaction, role: discord.Role = None):
        server = await Server.get_safe(interaction.guild_id)
        lang = self.get_lang(server.lang).manager_role
        server.manager_role = role.id if role else None
        await server.save()
        embed = BetterEmbed(BetterEmbed.OK)
        embed.set_default_thumbnail()
        embed.set_header(lang.title.get_string())
        if role is None:
            embed.description = lang.desc_unset.get_string()
        else:
            embed.description = lang.desc.get_string(role.mention)
        await interaction.response.send_message(embed=embed)

    @group.command(description="Configure the time offset")
    @app_commands.describe(offset="The hours your timezone defers from UTC")
    @has_manager_permission()
    async def timezone_offset(self, interaction: discord.Interaction,
                              offset: app_commands.Range[int, -23, 23]):
        server = await Server.get_safe(interaction.guild_id)
        lang = self.get_lang(server.lang).time_offset
        if offset is None:
            embed = BetterEmbed(BetterEmbed.DEFAULT)
            embed.set_default_thumbnail()
            embed.set_header(lang.title_help.get_string())
            embed.description = lang.desc_help.get_string("https://time.is/de/UTC")
            await interaction.response.send_message(embed=embed)
            return
        seconds = (offset * 3600) * - 1
        server.time_offset = seconds
        await server.save(update_fields=("time_offset",))
        embed = BetterEmbed(BetterEmbed.OK)
        embed.set_default_thumbnail()
        embed.set_header(lang.title_acive.get_string())
        embed.description = lang.desc_normal.get_string(offset)
        await interaction.response.send_message(embed=embed)

    @group.command(description="Configure delay when a lfg message should be deleted")
    @has_manager_permission()
    async def delete_lfg_after(self, interaction: discord.Interaction):
        server = await Server.get_safe(interaction.guild.id)
        lang = self.get_lang(server.lang).delay_setting
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_default_thumbnail()
        embed.set_header(lang.title.get_string())
        embed.description = lang.desc.get_string()
        strings = []
        indexes = []
        for k, v in StaticIdMaps.DELAY_STRINGS.items():
            indexes.append(k)
            strings.append(v)

        select = DynamicSelect(interaction.user, indexes, strings)
        await interaction.response.send_message(embed=embed, view=select, ephemeral=True)
        interaction: discord.Interaction
        interaction, index = await select.get_result()
        embed.set_header(lang.title_fin.get_string())
        embed.change_type(BetterEmbed.OK)
        embed.description = lang.desc_fin.get_string()
        server.delete_delay = index
        await server.save()
        await interaction.response.edit_message(view=None, embed=embed)

    @group.command(description="Add a log channel.")
    async def log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        server = await Server.get_safe(interaction.guild_id)
        lang = self.get_lang(server.lang).log_channel
        embed = BetterEmbed(BetterEmbed.OK)
        embed.set_header(lang.title.get_string())
        embed.description = lang.desc.get_string(channel.mention)
        embed.set_default_thumbnail()
        embed.footer_from_interaction(interaction)
        server.log_channel = channel.id
        await server.save()
        await interaction.response.send_message(embed=embed)


async def setup(bot: Neria):
    await bot.add_cog(ServerManagement(bot))
