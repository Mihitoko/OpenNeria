from typing import Any

import discord
from discord.ui import TextInput
from discord.ext.commands import converter

from utils.utils import parse_num, Missing, parse_datetime, get_roles_from_strings, parse_list


class ModalInputBase(TextInput):

    def __init__(self, entity_name, label, value=None, placeholder=None, **kwargs):
        super().__init__(label=label, placeholder=placeholder, default=value, **kwargs)
        self.entity_name = entity_name
        self.org_kwargs = kwargs

    def convert(self) -> Any:
        raise NotImplementedError


class NumberInputField(ModalInputBase):

    def __init__(self, entity_name, label, **kwargs):
        self.convert_cls = kwargs.pop("cls", int)
        self.min_value = kwargs.pop("min_value", None)
        self.max_value = kwargs.pop("max_value", None)
        self.default_value = kwargs.pop("default_value", Missing)
        super().__init__(entity_name, label, **kwargs)

    def convert(self) -> Any:
        return parse_num(
            self.value,
            min_value=self.min_value,
            max_value=self.max_value,
            cls=self.convert_cls,
            default=self.default_value
        )


class StringInputField(ModalInputBase):
    def convert(self) -> Any:
        return self.value


class DateInputField(ModalInputBase):
    def __init__(self, entity_name, label, offset, **kwargs):
        super().__init__(entity_name, label, **kwargs)
        self.offset = offset

    def convert(self) -> Any:
        return parse_datetime(self.value, self.offset).timestamp()


class RoleInputField(ModalInputBase):
    def __init__(self, entity_name, label, guild: discord.Guild, **kwargs):
        super().__init__(entity_name, label, **kwargs)
        self.guild = guild

    def convert(self) -> Any:
        return [role.id for role in get_roles_from_strings(self.guild, parse_list(self.value))]


class BoolInputField(ModalInputBase):
    def convert(self) -> bool:
        if len(self.value) == 0 and self.required is False:
            return False
        return converter._convert_to_bool(self.value)
