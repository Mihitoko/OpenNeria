import typing

import discord.ui
from discord import Interaction
from discord.ui import button, Item
from locales.gen import LanguageSchema, get_language

from persistence import EventStates
from persistence.models import Server, Event, EventPreset
from ui.modals.input_fields import NumberInputField, RoleInputField, BoolInputField
from ui.modals.settings_modals import ExtraSettingsModal, PresetSettingsModal, CreateEventSettings
from ui.views import LFGRegisterViewPersistent
from utils.overwrites import BetterEmbed, FixedView

if typing.TYPE_CHECKING:
    from bot import Neria


class DeleteEventView(discord.ui.View):
    def __init__(self, bot, event):
        super().__init__(timeout=60)
        self.event = event
        self.bot: "Neria" = bot
        self.message: typing.Union[discord.Message, None] = None

    def set_message(self, message):
        self.message = message

    @button(
        label="Restore event message",
        style=discord.ButtonStyle.green
    )
    async def restore(self, interaction: discord.Interaction, _):
        self.event.message_id = self.message.id
        await self.event.save()
        await interaction.response.edit_message(embed=(await self.bot.event_manager.build_event_embed(self.event)),
                                                view=LFGRegisterViewPersistent(self.bot))
        self.stop()

    @button(
        label="Delete event",
        style=discord.ButtonStyle.red
    )
    async def delete_event(self, interaction: discord.Interaction, _):
        server = await self.event.server
        lang: LanguageSchema.utils.delete_event_message = get_language(server.lang,
                                                                       LanguageSchema.utils.delete_event_message)
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_default_thumbnail()
        embed.set_header(lang.title_c.get_string())
        embed.description = lang.desc_c.get_string()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.event.state = EventStates.ENDED
        await self.event.save()
        await self.message.delete()
        self.stop()

    async def on_timeout(self) -> None:
        self.event.state = EventStates.ENDED
        await self.event.save()
        try:
            await self.message.delete()
        except discord.HTTPException:
            pass


class SettingsViewBase(FixedView):
    def __init__(self, server, db_data, member, bot: "Neria", require=True):
        super().__init__(timeout=120)
        self.require = require
        self.server: Server = server
        self.db_data: typing.Union[Event, EventPreset] = db_data
        self.member: discord.Member = member
        self.bot = bot

    def _get_modal(self):
        raise NotImplementedError

    @discord.ui.button(label="Settings")
    async def settings(self, interaction: discord.Interaction, _):
        await self.db_data.refresh_from_db()
        modal = self._get_modal()
        await interaction.response.send_modal(modal)
        new_interaction, result = await modal.get_result(180)
        await self.db_data.update_from_dict(result)
        await self.db_data.save()
        await self.on_settings_updated(new_interaction, self.db_data)

    @discord.ui.button(label="Extra settings")
    async def extra_settings(self, interaction: discord.Interaction, _):
        await self.db_data.refresh_from_db()
        role_names = []
        adv_settings = self.db_data.advanced_settings
        if adv_settings is not None:
            for role_id in self.db_data.advanced_settings.prio_roles:
                r = interaction.guild.get_role(role_id)
                if r:
                    role_names.append(r.name)
        modal = ExtraSettingsModal(
            [
                NumberInputField("min_gear_score", label="Minimum gearscore: ", placeholder="The minimum gearscore.",
                                 value=adv_settings.min_gear_score if adv_settings else None,
                                 required=False, default_value=None
                                 ),
                NumberInputField("max_same_class", label="Max duplicate classes:",
                                 placeholder="How many duplicate character classes do you allow?",
                                 value=adv_settings.max_same_class if adv_settings else None, required=False,
                                 default_value=None),
                NumberInputField("min_supporters", label="Min amount of support characters (defaults 0)",
                                 value=adv_settings.min_supporters if adv_settings else None,
                                 required=False, default_value=0),
                RoleInputField("prio_roles", label="Prioritize user with following roles: ",
                               placeholder="Type in the name or id off the role separated by a \",\"",
                               value=", ".join(role_names), guild=interaction.guild, required=False),
                NumberInputField("prio_time", label="Ignore roles time.",
                                 placeholder="Ignore user roles (in minute) before start.",
                                 value=adv_settings.prio_time if adv_settings else None, required=False,
                                 default_value=0)
            ],
            settings=self.db_data.advanced_settings,
            title="Edit preset"
        )
        await interaction.response.send_modal(modal)
        new_interaction, result = await modal.get_result()
        self.db_data.advanced_settings = result
        await self.db_data.save()
        await self.on_extra_settings_updated(new_interaction, self.db_data)

    @button(label="Extra settings 2")
    async def extra_set(self, interaction: discord.Interaction, _):
        await self.db_data.refresh_from_db()
        modal = ExtraSettingsModal(
            [
                RoleInputField("ping_roles", "Roles you want to ping when lfg is created", interaction.guild,
                               required=False),
                BoolInputField("text_on_exit", "Explanation on deregister",
                               placeholder="(yes or no) Requires log channel to be configured!", required=False)
            ],
            settings=self.db_data.advanced_settings,
            title="Edit preset"
        )
        await interaction.response.send_modal(modal)
        new_interaction, result = await modal.get_result()
        self.db_data.advanced_settings = result
        await self.db_data.save()
        await self.on_extra_settings_updated(new_interaction, self.db_data)

    async def on_settings_updated(self, interaction, data):
        raise NotImplementedError

    async def on_extra_settings_updated(self, interaction, data):
        raise NotImplementedError

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id == self.member.id:
            return True
        await interaction.response.defer()
        return False

    async def on_error(self, interaction: Interaction, error: Exception, item) -> None:
        self.bot.dispatch("ui_error", interaction, error)


class PresetSettingsView(SettingsViewBase):

    def __init__(self, server, db_data, member, bot: "Neria"):
        super().__init__(server, db_data, member, bot, require=not db_data.partial)
        self.basic_settings_cls = PresetSettingsModal

    def _get_modal(self):
        return PresetSettingsModal(db_data=self.db_data, title="Edit settings", require=self.require)

    async def on_settings_updated(self, interaction: discord.Interaction, data: EventPreset):
        server = await data.server
        await interaction.response.edit_message(embed=self.bot.event_manager.build_preset_embed(
            server.lang, data
        ))

    async def on_extra_settings_updated(self, interaction, data):
        await self.on_settings_updated(interaction, data)


class EventSettingsView(SettingsViewBase):

    def __init__(self, server, db_data, member, bot: "Neria"):
        super().__init__(server, db_data, member, bot)

    def _get_modal(self):
        return CreateEventSettings(self.server.time_offset,
                                   db_data=self.db_data, title="Edit settings", require=self.require)

    async def on_settings_updated(self, interaction, data):
        await interaction.response.send_message("👍", ephemeral=True)
        await self.bot.event_manager.update_event_message(data)

    async def on_extra_settings_updated(self, interaction, data):
        await self.on_settings_updated(interaction, data)
