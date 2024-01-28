from discord import TextStyle

from persistence.models import EvenDatatMeta, Event, PlayerCharacter, Server
from persistence.pydantic_models import AdvancedOptions
from ui.modals.input_fields import ModalInputBase, NumberInputField, StringInputField, DateInputField
from ui.modals.modal_base import BaseModal
from utils.utils import get_date_time_str


class _BasicEventSettings(BaseModal):

    def __init__(self, db_data: EvenDatatMeta = None, *args, **kwargs):
        self.db_data = db_data
        self.require = kwargs.pop("require", True)
        super().__init__(*args, **kwargs)

    def get_items(self):
        ret = [
            StringInputField("title", self.language.event_base.title_label.get_string(),
                             value=self.db_data.title if self.db_data else None, required=self.require),
            NumberInputField("max_players", label=self.language.event_base.max_player_label.get_string(),
                             value=self.db_data.max_players if self.db_data else "8", required=self.require),
            StringInputField("description", label=self.language.event_base.desc_label.get_string(),
                             value=self.db_data.description if self.db_data else None,
                             style=TextStyle.long, required=False, max_length=300)
        ]
        return ret

    async def get_result(self, timeout=60) -> dict:
        return await self.wait_result(timeout)


class PresetSettingsModal(_BasicEventSettings):
    def get_items(self):
        base = super(PresetSettingsModal, self).get_items()
        base.insert(0, StringInputField("name", label="Preset name", value=self.db_data.name if self.db_data else None))
        return base


class CreateEventSettings(_BasicEventSettings):
    def __init__(self, time_offset, db_data: Event = None, *args, **kwargs):
        self.time_offset = time_offset
        super().__init__(db_data, *args, **kwargs)
        self.db_data: Event = db_data

    def get_items(self):
        base = super(CreateEventSettings, self).get_items()
        base.insert(2, DateInputField("event_start", label=self.language.time_grab.time_label.get_string(),  # noqa
                                      offset=self.time_offset,
                                      value=get_date_time_str(self.db_data.event_start, self.time_offset)
                                      if isinstance(self.db_data, Event) else None,
                                      placeholder=self.language.time_grab.placeholder.get_string()
                                      ))
        return base


class ExtraSettingsModal(BaseModal):
    def __init__(self, items: list[ModalInputBase], settings: AdvancedOptions, *args, **kwargs):
        self.items = items
        self.settings = settings
        super().__init__(*args, **kwargs)

    async def get_result(self, timeout=60):
        interaction, result_dict = await self.wait_result(timeout)
        if self.settings:
            result = self.settings.copy(update=result_dict)
            return interaction, result
        return interaction, AdvancedOptions(**result_dict)

    def get_items(self):
        return self.items


class CharacterCreateModal(BaseModal):
    def __init__(self, *args, character: PlayerCharacter = None, **kwargs):
        self.character: PlayerCharacter = character
        super().__init__(*args, **kwargs)

    async def get_result(self, timeout=60):
        return await self.wait_result(timeout)

    def get_items(self):
        lang = self.language.char_create
        name = self.character.character_name if self.character else None
        gs = self.character.item_lvl if self.character else None
        return [
            StringInputField("character_name", label=lang.name_label.get_string(),
                             placeholder=lang.name_placeholder.get_string(), value=name),
            NumberInputField("item_lvl", label=lang.gs_label.get_string(), placeholder=lang.gs_placeholder.get_string(),
                             value=gs, cls=float)
        ]


class GetTimeModal(BaseModal):
    def __init__(self, server: Server, *args, **kwargs):
        kwargs["lang"] = server.lang
        self.server = server
        super().__init__(*args, **kwargs)

    async def get_result(self, timeout=60):
        interaction, result_dict = await self.wait_result(timeout)
        return interaction, result_dict["time"]

    def get_items(self):
        return [
            DateInputField("time",
                           self.language.time_grab.time_label.get_string(),
                           self.server.time_offset,
                           placeholder=self.language.time_grab.placeholder.get_string())
        ]
