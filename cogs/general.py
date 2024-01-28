import io
import time

import discord
from discord import app_commands

from bot import Neria
from persistence.models import Server, Users
from locales.gen import LanguageSchema
from utils.config_manager import ConfigManager
from utils.media_manager import MediaManager
from utils.overwrites import ExtCog, BetterEmbed
from utils.static import StaticIdMaps
from utils.utils import strip_text, get_message_link, build_fields


class General(ExtCog):

    def __init__(self, bot: Neria):
        self.bot: Neria = bot

    def get_lang(self, lang: str) -> LanguageSchema.Commands.General:
        return self.get_lang_by_reference(lang, LanguageSchema.Commands.General)

    @app_commands.command(description="Shows commands")
    async def help(self, interaction: discord.Interaction):
        server = await Server.get_safe(interaction.guild.id)
        lang_adv: LanguageSchema.Commands.settings.time_offset = self.get_lang_by_reference(server.lang,
                                                                                            LanguageSchema.Commands.
                                                                                            settings.time_offset)
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_header("Help")
        embed.description = self.get_lang(server.lang).help.desc.get_string("https://discord.gg/7q2aGpYQxS")
        embed.add_field(name=MediaManager.get_emoji("event_infos") + lang_adv.title_help.get_string(),
                        value=lang_adv.desc_help.get_string("https://time.is/de/UTC"))
        embed.set_footer(icon_url=interaction.user.avatar or interaction.user.default_avatar, text="Bot created by Mihito")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(description="Shows status of Lost Ark severs")
    async def server_status(self, interaction: discord.Interaction):
        data: dict = self.bot.scheduler.server_status_dict
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_header("Server Status")
        embed.set_default_thumbnail()
        q = []
        embed.description = f"**Note**: This embed reflects " \
                            f"[this](https://www.playlostark.com/de-de/support/server-status) website.\n" \
                            f"If some servers are not listed the site does not hold information for them.\n\n" \
                            f"{MediaManager.get_emoji('good')} **Okay**\n{MediaManager.get_emoji('busy')} **Busy**\n" \
                            f"{MediaManager.get_emoji('full')} **Full**\n{MediaManager.get_emoji('maintenance')}" \
                            f"**Maintenance**"
        for k, v in data.items():
            value = io.StringIO()
            for i in v:
                if i['status'] != "good":
                    name = f"**{i['name']}**"
                else:
                    name = i["name"]
                value.write(f"{MediaManager.get_emoji(i['status'])} | {name}\n")
            q.append((k, value.getvalue()))
        for i in sorted(q, key=lambda item: len(item[1].split("\n")), reverse=True):
            embed.add_field(name=i[0], value=i[1])

        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Infos about this server")
    async def server_info(self, interaction: discord.Interaction):
        server = await Server.get_safe(interaction.guild.id)
        lang = self.get_lang(server.lang).server_info
        presets = await server.event_presets
        preset_count = len(presets)
        events = await server.fetch_active_events()
        event_count = len(events)
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_header(lang.header.get_string())
        embed.description = lang.desc.get_string(interaction.guild.name, server.offset_hours(), preset_count,
                                                 event_count,
                                                 StaticIdMaps.DELAY_STRINGS[server.delete_delay])
        embed.set_default_thumbnail()
        no_value = lang.no_event.get_string()
        event_strings = []
        for counter, event in enumerate(sorted(events, key=lambda i: i.event_start)):
            event_strings.append(lang.event_template.get_string(counter + 1, event.title, event.event_start,
                                                                event.get_msg_link(interaction.guild_id)))
        build_fields(embed, lang.event_header.get_string(MediaManager.get_emoji("event_infos")), event_strings,
                     no_value, spacer=False, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Show a users profile")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):
        server = await Server.get_safe(interaction.guild.id)
        lang = self.get_lang(server.lang).Profile
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_default_thumbnail()
        embed.footer_from_interaction(interaction)
        highest_char = None
        if not user:
            user = interaction.user
            embed.set_header(lang.title_self.get_string())
        else:
            embed.set_header(lang.title_other.get_string(user.name))
        db_user = await Users.get_safe(user.id)
        await db_user.fetch_characters()
        await db_user.fetch_registered_events()
        embed.description = lang.desc.get_string(user.mention)
        if len(db_user.characters) == 0:
            field_desc = lang.no_char.get_string()
        else:
            s = io.StringIO()
            for i in db_user.characters:
                s.write(lang.class_template.get_string(
                    MediaManager.get_emoji(i.character_class.emoji_name),
                    i.character_name, i.character_class.name, i.item_lvl
                ))
                if i.api_id:
                    if highest_char is None:
                        highest_char = i
                    elif i.item_lvl > highest_char.item_lvl:
                        highest_char = i

            field_desc = s.getvalue()
        embed.add_field(
            name=lang.char_field_title.get_string(MediaManager.get_emoji("default")),
            value=field_desc
        )
        if len([i for i in db_user.registered_for if not i.event.has_ended]) == 0:
            event_field_desc = lang.no_event.get_string()
        else:
            s = io.StringIO()
            counter = 1
            for register in db_user.registered_for:
                if register.event.has_ended:
                    continue
                s.write(lang.event_template.get_string(
                    counter, register.event.title, register.event.event_start,
                    get_message_link(interaction.guild.id, register.event.channel_id, register.event.message_id)))
                counter += 1
            event_field_desc = s.getvalue()
        embed.add_field(
            name=lang.event_tile.get_string(MediaManager.get_emoji("default")),
            value=event_field_desc,
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bot_info", description="Infos about Neria")
    async def _info(self, interaction: discord.Interaction):
        server = await Server.get_safe(interaction.guild.id)
        bot_stats = self.bot.stat_manager.stats
        lang = self.get_lang(server.lang).bot_info
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_header(lang.header.get_string())
        embed.add_field(
            name=lang.tech_header.get_string(MediaManager.get_emoji("event_infos")),
            value=lang.tech_desc.get_string()
        )
        embed.add_field(
            name=lang.stats_header.get_string(MediaManager.get_emoji("event_infos")),
            value=lang.stats_desc.get_string(bot_stats.guild_count, bot_stats.user_count, bot_stats.total_characters)
        )
        embed.set_default_thumbnail()
        embed.set_image(url=bot_stats.character_stats_url)
        await interaction.response.send_message(embed=embed)


async def setup(bot: Neria):
    await bot.add_cog(General(bot))
