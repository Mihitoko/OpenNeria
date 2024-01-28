import datetime
import time
import typing

import discord.ui
import pytz
from discord import Interaction, TextStyle
from discord.ui import button, Item
from locales.gen import LanguageSchema, get_language

from persistence.models import Event, EventRegister, Server, Users, PlayerCharacter
from errors import registration
from errors.basic import EventNotFound
from ui.modals.dynamic_modal import DynamicModal
from ui.modals.input_fields import StringInputField
from ui.views.selects import CharactersSelectView, SetReminderView
from utils.overwrites import FixedView, BetterEmbed
from utils.utils import Cooldown

if typing.TYPE_CHECKING:
    from bot import Neria


class LFGPingViewPersistent(FixedView):
    def __init__(self, bot: "Neria"):
        super(LFGPingViewPersistent, self).__init__(timeout=None)
        self.bot = bot
        self.cd = Cooldown(ttl=300)

    @button(
        label="DM all",
        custom_id="neria:lfg_dm_all",
        style=discord.ButtonStyle.blurple
    )
    async def dm_all_callback(self, interaction: discord.Interaction, _):
        event = await Event.get_or_none(message_id=interaction.message.id)
        await interaction.response.defer()
        await self.bot.event_manager.notify_all(event)

    @button(
        label="Ping all",
        custom_id="neria:lfg_ping_all",
        style=discord.ButtonStyle.blurple
    )
    async def ping_all_callback(self, interaction: discord.Interaction, _):
        event = await Event.get_or_none(message_id=interaction.message.id)
        await event.fetch_participants(include_users=True)
        pings = []
        for register in event.registered_users:
            pings.append(f"<@{register.user.id}>")
        await interaction.response.send_message(", ".join(pings))

    async def interaction_check(self, interaction: Interaction):
        event: "Event" = await Event.get(message_id=interaction.message.id).prefetch_related("creator")
        creator = event.creator.id
        if creator == interaction.user.id:
            if not self.cd.can_execute((interaction.message.id, interaction.user.id)):
                embed = BetterEmbed(BetterEmbed.ERROR)
                embed.set_header("Cooldown")
                remain = self.cd.get_remaining((interaction.message.id, interaction.user.id))
                embed.description = f"Sorry I'm busy right now.\nPlease try again in {remain} seconds."
                embed.set_default_thumbnail()
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
            self.cd.add_item((interaction.message.id, interaction.user.id))
            return True
        await interaction.response.defer()
        return False


class LFGRegisterViewPersistent(FixedView):
    def __init__(self, bot: "Neria"):
        super(LFGRegisterViewPersistent, self).__init__(timeout=None)
        self.bot = bot
        self.cd = Cooldown(10)

    @button(
        label="Register",
        custom_id="neria:lfg_register_main",
        style=discord.ButtonStyle.green
    )
    async def register_callback_button(self, interaction: discord.Interaction, _):
        await self.register(interaction, False)

    @button(
        label="Register as substitute",
        custom_id="neria:lfg_register_secondary",
        style=discord.ButtonStyle.blurple
    )
    async def register_secondary_callback(self, interaction: discord.Interaction, _):
        await self.register(interaction, True)

    @button(
        label="Deregister",
        custom_id="neria:lfg_deregister",
        style=discord.ButtonStyle.secondary
    )
    async def deregister_callback(self, interaction: discord.Interaction, _):
        lfg_search = await self.get_event_or_rise(interaction.message.id)
        await lfg_search.fetch_participants()
        server = await lfg_search.server
        lang: LanguageSchema.utils.deregister_callback = get_language(server.lang,
                                                                      LanguageSchema.utils.deregister_callback)
        registration = await EventRegister.get_or_none(user_id=interaction.user.id, event_id=lfg_search.id)
        if not registration:
            return
        if lfg_search.advanced_settings and lfg_search.advanced_settings.text_on_exit:
            modal_items = [StringInputField("text", lang.item_label.get_string(),
                                            style=TextStyle.long, max_length=500)]
            modal = DynamicModal(modal_items, title=lang.modal_title.get_string())

            await interaction.response.send_modal(modal)
            new_interaction, result = await modal.get_result()
            embed = BetterEmbed(BetterEmbed.DEFAULT)
            embed.set_header(lang.success_header.get_string())
            embed.set_default_thumbnail()
            embed.description = lang.success_desc.get_string()
            await new_interaction.response.send_message(embed=embed, ephemeral=True)
            channel = self.bot.get_channel(server.log_channel)
            if channel:
                embed.set_header(lang.report_title.get_string(new_interaction.user.name))
                embed.description = lang.report_desc.get_string(new_interaction.user.mention, lfg_search.title,
                                                                result["text"])
                await channel.send(embed=embed)

        else:
            await interaction.response.defer()
        await registration.delete()
        e = await self.bot.event_manager.build_event_embed(lfg_search)
        await interaction.followup.edit_message(interaction.message.id, embed=e)

    @discord.ui.button(
        label="Kick",
        custom_id="neria:lfg_kick",
        style=discord.ButtonStyle.danger
    )
    async def kick_part(self, interaction: discord.Interaction, _):
        event = await self.get_event_or_rise(interaction.message.id)
        server = await event.server
        lang: LanguageSchema.utils.kick_callback = get_language(server.lang, LanguageSchema.utils.kick_callback)
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_default_thumbnail()
        if interaction.user.id != (await event.creator).id:
            embed.change_type(BetterEmbed.ERROR)
            embed.description = lang.no_perm.get_string()
            embed.set_header(lang.error_header.get_string())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await event.fetch_participants(include_users=True)
        to_select = [user.character for user in event.registered_users]
        if len(to_select) > 25:
            embed.change_type(BetterEmbed.ERROR)
            embed.description = lang.to_many_parts.get_string()
            embed.set_header(lang.error_header.get_string())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if len(to_select) == 0:
            embed.change_type(BetterEmbed.ERROR)
            embed.description = lang.no_part.get_string()
            embed.set_header(lang.error_header.get_string())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        view = CharactersSelectView(interaction.user, to_select)
        embed.set_header(lang.header.get_string())
        embed.description = lang.desc.get_string()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        interaction_new, result = await view.get_result()
        embed.change_type(BetterEmbed.OK)
        db_user = await result.user
        embed.description = lang.suc.get_string(result.character_name,
                                                interaction_new.client.get_user(db_user.id).mention)
        embed.set_header(lang.suc_header.get_string())
        for player in event.registered_users:
            if player.character.id == result.id:
                await player.delete()
                break

        await interaction_new.response.edit_message(embed=embed, view=None)
        e = await self.bot.event_manager.build_event_embed(event)
        await interaction.followup.edit_message(interaction.message.id, embed=e)

    @button(
        label="Remind me overwrite",
        style=discord.ButtonStyle.blurple,
        custom_id="neria:remind_me"
    )
    async def remind_me(self, interaction: discord.Interaction, _):
        event = await self.get_event_or_rise(interaction.message.id)
        server = await event.server
        registration_ = await EventRegister.get_or_none(event=event, user_id=interaction.user.id)
        if registration_ is None:
            await interaction.response.send_message("Not registered", ephemeral=True)
            return
        lang: LanguageSchema.utils.set_reminder = get_language(server.lang, LanguageSchema.utils.set_reminder)
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_header(lang.header.get_string())
        view = SetReminderView(interaction.user)
        embed.description = lang.desc.get_string()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        new_interaction, result = await view.get_result()
        registration_.notify_before = result
        await registration_.save()
        embed.change_type(BetterEmbed.OK)
        embed.set_header(lang.on_title.get_string())
        embed.description = lang.desc_ok.get_string()
        await new_interaction.response.edit_message(embed=embed, view=None)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not self.cd.can_execute((interaction.message.id, interaction.user.id)) and not self.bot.is_debug():
            embed = BetterEmbed(BetterEmbed.ERROR)
            embed.set_header("Cooldown")
            remain = self.cd.get_remaining((interaction.message.id, interaction.user.id))
            embed.description = f"Sorry I'm busy right now.\nPlease try again in {remain} seconds."
            embed.set_default_thumbnail()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False

        self.cd.add_item((interaction.message.id, interaction.user.id))
        return True

    async def register(self, interaction: discord.Interaction, secondary):
        server = await Server.get_safe(interaction.guild.id)
        db_user = await Users.get_safe(interaction.user.id)
        await db_user.fetch_characters()
        lfg_search = await self.get_event_or_rise(interaction.message.id)
        await lfg_search.fetch_participants(include_users=True)
        registration_event = await EventRegister.get_or_none(user_id=db_user.id, event_id=lfg_search.id)
        lang: LanguageSchema.utils.register_callback = get_language(server.lang,
                                                                    LanguageSchema.utils.register_callback)
        discord_user = interaction.guild.get_member(db_user.id)
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        if registration_event:
            # Check if we just want to switch sides
            await interaction.response.defer()
            if registration_event.substitute != secondary:
                if not secondary:
                    await registration_event.fetch_character()
                    self.can_register(server, discord_user, lfg_search)
                    self.filter_register_characters(lfg_search,
                                                    [registration_event.character])  # Dirty why of reusing the method
                registration_event.substitute = not registration_event.substitute  # Negate = Switching sides
                registration_event.registered_at = int(time.time())
                await registration_event.save()
                embed = await self.bot.event_manager.build_event_embed(lfg_search)
                await interaction.followup.edit_message(interaction.message.id, embed=embed)
                return
            else:
                return

        if lfg_search.registered_count >= lfg_search.max_players and not secondary:
            embed.change_type(BetterEmbed.ERROR)
            embed.set_header(lang.max_players_title.get_string())
            embed.description = lang.max_players_desc.get_string()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if len(db_user.characters) == 0:
            embed.set_header(lang.no_char_title.get_string())
            embed.description = lang.no_char_desc.get_string()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if not secondary:
            self.can_register(server, discord_user, lfg_search)
            filtered_characters = self.filter_register_characters(lfg_search, db_user.characters)
        else:
            filtered_characters = db_user.characters
        embed.set_header(lang.title.get_string())
        embed.description = lang.desc.get_string()
        view = CharactersSelectView(discord_user, filtered_characters)  # noqa
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        new_interaction, result = await view.get_result()
        # Check if there is no entry in the db to ensure that we don't insert twice.
        # A lock would be better but im lazy
        # Todo: Implement lock
        second_register_check = await EventRegister.get_or_none(user_id=db_user.id, event_id=lfg_search.id)
        if second_register_check is not None:
            await new_interaction.response.defer()
            return
        await EventRegister.create(
            event=lfg_search,
            user=db_user,
            character=result,
            registered_at=int(time.time()),
            substitute=secondary
        )
        embed.description = lang.fin.get_string()
        embed.change_type(BetterEmbed.OK)
        await new_interaction.response.edit_message(embed=embed, view=None)
        embed = await self.bot.event_manager.build_event_embed(lfg_search)
        await interaction.followup.edit_message(interaction.message.id, embed=embed)

    def can_register(self, server: Server, user: discord.Member, event: Event):
        if event.advanced_settings is None:
            return
        role_ids = event.advanced_settings.prio_roles
        prio_roles = []
        for i in role_ids:
            role = user.guild.get_role(i)
            if role:
                prio_roles.append(role)

        if len(prio_roles) == 0:
            return

        seconds_ignore = event.advanced_settings.prio_time * 60
        now = datetime.datetime.now(tz=pytz.UTC).timestamp()
        starts_in = event.event_start - now
        if (starts_in - seconds_ignore) < 0:
            return
        for role in prio_roles:
            if role in user.roles:
                return
        raise registration.NoPrioRoleError(prio_roles, event.event_start - seconds_ignore)

    def filter_register_characters(self, event: Event, character_list: list[PlayerCharacter]):
        """
        Filter the users selection based of the advanced settings
        :param character_list:
        :param event:
        :return:
        """
        character_list = [i for i in character_list]
        space_left = event.max_players - event.registered_count
        if space_left <= 0:
            raise registration.PlayersFullError(event.max_players)

        if event.advanced_settings is None:
            return character_list
        filtered_list = []

        amount_support = 0
        for entry in event.registered_users:
            if entry.substitute:
                continue
            if entry.character.character_class.has_tag("support"):
                amount_support += 1

        registered_class_ids = []
        for entry in event.registered_users:
            if not entry.substitute:
                registered_class_ids.append(entry.character.character_class.class_id)

        if event.advanced_settings.max_same_class is not None:
            for character in character_list:
                if not (registered_class_ids.count(character.character_class.class_id) >=
                        event.advanced_settings.max_same_class):
                    filtered_list.append(character)

        else:
            filtered_list = character_list.copy()

        if event.advanced_settings.min_gear_score is not None:
            for character in filtered_list.copy():
                if not character.item_lvl >= event.advanced_settings.min_gear_score:
                    filtered_list.remove(character)

        supports_required = event.advanced_settings.min_supporters - amount_support
        if space_left <= supports_required:
            for char in filtered_list.copy():
                if not char.character_class.has_tag("support"):
                    filtered_list.remove(char)

        if len(filtered_list) == 0:
            raise registration.RequirementsNotMetError

        return filtered_list

    async def get_event_or_rise(self, id_):
        event = await Event.get_or_none(message_id=id_)
        if event is None or event.has_ended:
            raise EventNotFound(id_)
        return event

    async def on_error(self, interaction: Interaction, error: Exception, item) -> None:
        interaction.client.dispatch("ui_error", interaction, error)
