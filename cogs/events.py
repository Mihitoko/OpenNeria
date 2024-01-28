import asyncio

import discord
from discord import RawMessageDeleteEvent, AllowedMentions, Interaction, app_commands, Permissions
from discord.app_commands import Group
from discord.errors import HTTPException
from locales.gen import LanguageSchema, get_language

import utils.async_checks
from bot import Neria
from persistence import EventStates
from persistence.models import Server, Users, Event, EventPreset, MessageDeleteQueue, EventRegister
from errors.basic import NotAPreset
from ui.modals.settings_modals import PresetSettingsModal, CreateEventSettings, GetTimeModal
from ui.views import LFGRegisterViewPersistent, PresetSettingsView, DeleteEventView, \
    LFGPingViewPersistent, EventSettingsView
from ui.views.selects import ChooseEventSelect
from utils import static
from utils.auto_complete_callbacks import AutoCompleteCallbacks
from utils.config_manager import ConfigManager
from utils.media_manager import MediaManager
from utils.overwrites import ExtCog, BetterEmbed
from utils.static import DeleteTimeEnum
from utils.utils import build_fields


class EventCog(ExtCog):
    event_group = Group(name="lfg", description="Manage your account.",
                        guild_ids=ConfigManager.get_debug_guild_when_debug())

    def __init__(self, bot: Neria):
        self.bot: Neria = bot

    def get_lang(self, lang: str) -> LanguageSchema.Commands.Event:
        return self.get_lang_by_reference(lang, LanguageSchema.Commands.Event)

    @ExtCog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        if payload.guild_id is None:
            return
        event = await Event.get_or_none(message_id=payload.message_id, state=EventStates.PLANING)
        if event is None:
            return
        server = await event.server
        lang: LanguageSchema.utils.delete_event_message = get_language(server.lang,
                                                                       LanguageSchema.utils.delete_event_message)
        embed = BetterEmbed(BetterEmbed.INFO)
        embed.set_default_thumbnail()
        embed.set_header(lang.title_q.get_string())
        embed.description = lang.title_desc.get_string()
        channel = self.bot.get_channel(payload.channel_id)
        view = DeleteEventView(self.bot, event)
        try:
            m = await channel.send(embed=embed, view=view)
            view.set_message(m)
        except discord.HTTPException:
            event.state = EventStates.ENDED
            await event.save()

    @event_group.command(description="Schedule a lfg")
    @app_commands.describe(preset="Choose a preset",
                           weekly="Lfg is automatically rescheduled one week in the future when it ends")
    @app_commands.autocomplete(preset=AutoCompleteCallbacks.query_presets)
    async def schedule(self, interaction: Interaction,
                       preset: str = None, weekly: bool = False):
        server = await Server.get_safe(interaction.guild.id)
        user = await Users.get_safe(interaction.user.id)
        lang = self.get_lang(server.lang).schedule
        advanced_settings = None
        if weekly:
            perms: Permissions = interaction.channel.permissions_for(interaction.guild.me)
            if not perms.send_messages:
                embed = BetterEmbed(BetterEmbed.INFO)
                embed.set_header(lang.weekly_no_perms.get_string())
                embed.description = lang.weekly_no_perms_desc.get_string()
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        if preset is None:
            modal = CreateEventSettings(server.time_offset, title="Create the event")
            await interaction.response.send_modal(modal)
            interaction, result = await modal.get_result(500)
            timestamp = result["event_start"]
            desc = result["description"]
            player_count = result["max_players"]
            title = result["title"]
        else:
            await server.fetch_event_presets()
            for remote_preset in server.event_presets:
                if remote_preset.name.lower() == preset.lower():
                    actual_preset = remote_preset
                    break
            else:
                raise NotAPreset(preset)
            if actual_preset.partial:
                modal = CreateEventSettings(server.time_offset, db_data=actual_preset, title="Create Event")
                await interaction.response.send_modal(modal)
                interaction, result = await modal.get_result(500)
                timestamp = result["event_start"]
                desc = result["description"]
                player_count = result["max_players"]
                title = result["title"]
                advanced_settings = actual_preset.advanced_settings
            else:
                modal = GetTimeModal(server, title="Type in starting time")
                await interaction.response.send_modal(modal)
                interaction, timestamp = await modal.get_result(500)
                player_count = actual_preset.max_players
                title = actual_preset.title
                desc = actual_preset.description
                advanced_settings = actual_preset.advanced_settings
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_header(lang.loading_title.get_string())
        mentions = []
        if advanced_settings:
            for i in advanced_settings.ping_roles:
                mentions.append(interaction.guild.get_role(i).mention)
        else:
            mentions = None
        await interaction.response.send_message(", ".join(mentions) if advanced_settings else None,
                                                embed=embed, view=LFGRegisterViewPersistent(self.bot),
                                                allowed_mentions=AllowedMentions.all())
        msg = await interaction.original_response()
        event = await Event.create(
            creator=user,
            server=server,
            event_start=timestamp,
            message_id=msg.id,
            description=desc if desc else "",
            title=title,
            max_players=player_count,
            channel_id=msg.channel.id,
            advanced_settings=advanced_settings,
            weekly=weekly
        )
        e = await self.bot.event_manager.build_event_embed(event)
        await interaction.followup.edit_message(msg.id, embed=e)

    @event_group.command(description="Cancel a running lfg")
    async def cancel(self, interaction: Interaction, notify: bool = True):
        server = await Server.get_safe(interaction.guild.id)
        user = await Users.get_safe(interaction.user.id)
        active_events = await server.fetch_active_events()
        lang = self.get_lang(server.lang).cancel
        to_choose = []
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        for event in active_events:
            await event.fetch_creator()
            if event.creator.id == user.id:
                to_choose.append(event)
        if len(to_choose) == 0:
            embed.change_type(BetterEmbed.INFO)
            embed.set_header(lang.title_no_lfg.get_string())
            embed.description = lang.desc_not_lfg.get_string()
            await interaction.response.send_message(embed=embed)
            return

        select = ChooseEventSelect(interaction.user, to_choose, server)
        embed.footer_from_interaction(interaction)
        embed.set_default_thumbnail()
        embed.set_header(lang.title.get_string())
        embed.description = lang.desc.get_string()
        await interaction.response.send_message(embed=embed, view=select, ephemeral=True)
        interaction, result = await select.get_result()
        t = result.title
        embed.change_type(BetterEmbed.OK)
        embed.set_header(lang.title_ok.get_string())
        embed.description = lang.desc_ok.get_string(t)
        await interaction.response.edit_message(embed=embed, view=None)
        if notify:
            await self.notify_canceled(result)
        result.state = EventStates.ENDED
        await result.save()
        await self.delete_event_message(result)

    @event_group.command(description="Edit a running lfg")
    async def edit(self, interaction: Interaction):
        server = await Server.get_safe(interaction.guild.id)
        user = await Users.get_safe(interaction.user.id)
        active_events = await server.fetch_active_events()
        lang = self.get_lang(server.lang).edit
        to_choose = []
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        for event in active_events:
            await event.fetch_creator()
            if event.creator.id == user.id:
                to_choose.append(event)
        if len(to_choose) == 0:
            embed.change_type(BetterEmbed.INFO)
            embed.set_header(lang.title_no_lfg.get_string())
            embed.description = lang.desc_not_lfg.get_string()
            await interaction.response.send_message(embed=embed)
            return
        select = ChooseEventSelect(interaction.user, to_choose, server)
        embed.footer_from_interaction(interaction)
        embed.set_default_thumbnail()
        embed.set_header(lang.title.get_string())
        embed.description = lang.desc.get_string()
        await interaction.response.send_message(embed=embed, view=select, ephemeral=True)
        interaction, result = await select.get_result()
        embed.change_type(BetterEmbed.DEFAULT)
        embed.set_header(lang.title_ok.get_string())
        embed.description = lang.desc_ok.get_string()
        view = EventSettingsView(server, result, interaction.user, self.bot)
        await interaction.response.edit_message(embed=embed, view=view)

    @event_group.command(description="Create a server wide lfg preset. Only bot managers can use this.")
    @app_commands.describe(partial="Changeable preset on lfg creation.")
    @utils.async_checks.has_manager_permission()
    async def create_preset(self, interaction: Interaction,
                            partial: bool = False):
        server = await Server.get_safe(interaction.guild.id)
        presets = await server.event_presets
        lang = self.get_lang(server.lang).create_preset
        if len(presets) >= 25:
            embed = BetterEmbed(BetterEmbed.INFO)
            embed.set_header(lang.max_preset_title.get_string())
            embed.description = lang.max_preset_desc.get_string()
            embed.set_default_thumbnail()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        modal = PresetSettingsModal(title=lang.modal_title.get_string(), require=not partial)
        await interaction.response.send_modal(modal)
        interaction, result_dict = await modal.get_result(180)
        preset_name = result_dict["name"] if not partial else result_dict["name"] + " (partial)"
        result_dict["name"] = preset_name
        event_preset = await EventPreset.create(
            **result_dict,
            partial=partial,
            server=server
        )
        embed = self.build_preset_embed(server.lang, event_preset)
        view = PresetSettingsView(server, event_preset, interaction.user, self.bot)
        await interaction.response.send_message(embed=embed, view=view)

    @event_group.command(description="Delete a server wide lfg preset. Only bot managers can use this.")
    @app_commands.autocomplete(preset=AutoCompleteCallbacks.query_presets)
    @utils.async_checks.has_manager_permission()
    async def delete_preset(self, interaction: Interaction,
                            preset: str):
        server = await Server.get_safe(interaction.guild.id)
        lang = self.get_lang(server.lang).delete_preset
        await server.fetch_event_presets()
        for remote_preset in server.event_presets:
            if remote_preset.name.lower() == preset.lower():
                actual_preset = remote_preset
                break
        else:
            raise NotAPreset(preset)
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_default_thumbnail()
        embed.set_header(lang.title.get_string())
        embed.description = lang.desc.get_string(actual_preset.name)
        await actual_preset.delete()
        await interaction.response.send_message(embed=embed)

    @event_group.command(description="Shows a preset")
    @app_commands.autocomplete(preset=AutoCompleteCallbacks.query_presets)
    @utils.async_checks.has_manager_permission()
    async def show_preset(self, interaction: Interaction,
                          preset: str):
        server = await Server.get_safe(interaction.guild.id)
        await server.fetch_event_presets()
        for remote_preset in server.event_presets:
            if remote_preset.name.lower() == preset.lower():
                actual_preset = remote_preset
                break
        else:
            raise NotAPreset(preset)
        await actual_preset.fetch_related("server")
        await interaction.response.send_message(embed=self.build_preset_embed(server.lang, actual_preset),
                                                view=PresetSettingsView(
                                                    server, actual_preset, interaction.user, self.bot
                                                ))

    def build_preset_embed(self, lang, event_preset: EventPreset):
        lang = self.get_lang(lang).create_preset
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_header(lang.title.get_string(event_preset.name))
        embed.description = lang.desc.get_string(event_preset.name)
        embed.add_field(
            name=lang.sum_title.get_string(MediaManager.get_emoji("event_infos")),
            value=lang.summary.get_string(
                event_preset.name,
                event_preset.title,
                event_preset.max_players,
                event_preset.description
            )
        )
        if event_preset.advanced_settings:
            embed.add_field(name="\u200b", value="\u200b")
            guild = self.bot.get_guild(event_preset.server.id)

            def resolve_roles(role_list):
                roles = []
                for role_id in role_list:
                    role = guild.get_role(role_id)
                    if role:
                        roles.append(role.mention)
                return roles

            prio_roles = resolve_roles(event_preset.advanced_settings.prio_roles)
            ping_roles = resolve_roles(event_preset.advanced_settings.ping_roles)
            embed.add_field(
                name=lang.advanced_title.get_string(MediaManager.get_emoji("event_infos")),
                value=lang.advanced_desc.get_string(
                    event_preset.advanced_settings.min_gear_score,
                    event_preset.advanced_settings.max_same_class,
                    event_preset.advanced_settings.min_supporters,
                    ", ".join(prio_roles) if len(prio_roles) > 0 else "`None`",
                    event_preset.advanced_settings.prio_time,
                    ", ".join(ping_roles) if len(ping_roles) > 0 else "`None`",
                    event_preset.advanced_settings.text_on_exit
                )
            )
        embed.set_default_thumbnail()
        return embed

    async def build_event_embed(self, event: Event):
        await event.fetch_creator()
        await event.fetch_server()
        discord_user = self.bot.get_user(event.creator.id)
        lang: LanguageSchema.utils.event_message = get_language(
            event.server.lang, LanguageSchema.utils.event_message)

        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_header(event.title)
        full_desc = event.description + lang.desc_suffix.get_string()
        embed.description = full_desc
        embed.add_field(name=lang.info_header.get_string(MediaManager.get_emoji("event_infos")),
                        value=lang.info_field.get_string(discord_user.mention,
                                                         event.event_start, event.max_players), inline=False)
        await event.fetch_participants()
        main = []
        sub = []

        def foo(character, li):
            li.append(lang.class_template.get_string(
                MediaManager.get_emoji(character.character_class.emoji_name),
                character.character_name,
                character.character_class.name,
                character.item_lvl
            ))

        counter = 0
        for register in event.registered_users:
            await register.fetch_character()
            if register.substitute:
                foo(register.character, sub)
                continue
            if register.character.character_class.has_tag("support"):
                counter += 1
            foo(register.character, main)

        if event.advanced_settings:
            roles = []
            guild = self.bot.get_guild(event.server.id)
            for role_id in event.advanced_settings.prio_roles:
                role = guild.get_role(role_id)
                if role:
                    roles.append(role.mention)
            embed.add_field(
                name=lang.advanced_settings.get_string(MediaManager.get_emoji("event_infos")),
                value=lang.advanced_value.get_string(
                    event.advanced_settings.min_gear_score,
                    event.advanced_settings.max_same_class,
                    counter,
                    event.advanced_settings.min_supporters,
                    ", ".join(roles) if len(roles) > 0 else "`None`",
                    event.advanced_settings.prio_time,
                    event.advanced_settings.text_on_exit
                ), inline=False
            )

        build_fields(embed, lang.character_header.get_string(
            MediaManager.get_emoji("participant"),
            event.registered_count, event.max_players
        ), main, lang.no_part.get_string())

        build_fields(embed, lang.subtitudes.get_string(MediaManager.get_emoji("substitute")), sub,
                     lang.no_sub.get_string())
        embed.set_default_thumbnail()
        return embed

    async def update_event_message(self, event: Event):
        channel = self.bot.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)
        embed = await self.build_event_embed(event)
        await message.edit(embed=embed)

    async def notify_canceled(self, event: Event, user: discord.User = None):
        server = await event.server
        lang: LanguageSchema.utils.notify_cancel = get_language(server.lang, LanguageSchema.utils.notify_cancel)
        await event.fetch_participants(include_users=True)
        await event.fetch_creator()
        q = []
        embed = BetterEmbed(BetterEmbed.INFO)
        embed.description = lang.desc.get_string(
            self.bot.get_user(event.creator.id).mention if not user else user.mention, event.title, event.event_start)
        embed.set_header(lang.title.get_string())
        for entry in event.registered_users:
            if entry.user.id != event.creator.id:
                discord_user = self.bot.get_user(entry.user.id)
                q.append(discord_user.send(embed=embed))
        await asyncio.gather(*q, return_exceptions=True)

    async def on_event_start(self, event: Event):
        server = await event.server
        await self.change_view_event_message(event, LFGPingViewPersistent(self.bot))
        if not DeleteTimeEnum.NEVER == server.delete_delay:
            await MessageDeleteQueue.create(id=event.message_id,
                                            delete_at=static.StaticIdMaps.DELETE_DELAYS[server.delete_delay] +
                                            event.event_start, channel_id=event.channel_id)

        if event.weekly:
            channel = self.bot.get_channel(event.channel_id)
            if channel:
                guild = self.bot.get_guild(server.id)
                if not channel.permissions_for(guild.me).send_messages:
                    return
                content = None
                if event.advanced_settings:
                    s = []
                    mentions = event.advanced_settings.ping_roles
                    for i in mentions:
                        s.append(f"<@&{i}>")
                    if len(s) > 0:
                        content = ", ".join(s)
                pre_embed = BetterEmbed(BetterEmbed.DEFAULT)
                pre_embed.set_header("Pending lfg creation")
                pre_embed.description = "Recreating weekly lfg...."
                msg = await channel.send(content=content, embed=pre_embed, view=LFGRegisterViewPersistent(self.bot),
                                         allowed_mentions=AllowedMentions.all())
                creator = await event.creator
                new_event = await Event.create(
                    creator=creator,
                    server=server,
                    event_start=event.event_start + 604800,
                    message_id=msg.id,
                    description=event.description,
                    title=event.title,
                    max_players=event.max_players,
                    channel_id=msg.channel.id,
                    advanced_settings=event.advanced_settings,
                    weekly=True
                )
                embed = await self.build_event_embed(new_event)
                await msg.edit(embed=embed)

    async def notify_all(self, event: Event):
        await event.fetch_participants(include_users=True)
        await event.fetch_server()
        for register in event.registered_users:
            await self.notify_start_user(register)

    async def notify_start_user(self, registered_entry: EventRegister):
        event = await registered_entry.event
        server = await event.server
        user = registered_entry.user
        if not isinstance(user, Users):
            user = await user
        discord_user = self.bot.get_user(user.id)
        if discord_user is None:
            return
        lang: LanguageSchema.utils.notify_start = get_language(server.lang, LanguageSchema.utils.notify_start)
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_header(lang.title.get_string())
        embed.set_default_thumbnail()
        embed.description = lang.desc.get_string(discord_user.mention, event.title, event.event_start)
        try:
            await discord_user.send(embed=embed)
        except HTTPException:
            pass

    async def change_view_event_message(self, event: Event, view=None):
        try:
            channel = self.bot.get_channel(event.channel_id)
            if channel is None:
                return
            msg = await channel.fetch_message(event.message_id)
            await msg.edit(view=view)
        except discord.HTTPException:
            return

    async def delete_event_message(self, event: Event):
        try:
            channel = self.bot.get_channel(event.channel_id)
            if channel is None:
                return
            msg = await channel.fetch_message(event.message_id)
            await msg.delete()
        except discord.HTTPException:
            return


async def setup(bot: Neria):
    await bot.add_cog(EventCog(bot))
