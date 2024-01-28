from discord.app_commands import AppCommandError
from discord.errors import DiscordException


class ToManyCharacters(DiscordException):
    def __str__(self):
        return "The invoker has to many characters"


class NumberConversionError(DiscordException):
    def __init__(self, n):
        self.num = n


class DateConversionError(DiscordException):
    def __init__(self, m: str):
        self.date_str = m


class NotAPreset(DiscordException):
    def __init__(self, name):
        self.name = name


class ModalInteractionCallbackError(DiscordException):
    def __init__(self, inner, interaction):
        self.real_exception = inner
        self.interaction = interaction


class DateTimeInPast(DiscordException):
    def __init__(self, datetime):
        self.date = datetime


class InvalidNumber(DiscordException):
    def __init__(self, num):
        self.num = num


class EventNotFound(DiscordException):
    def __init__(self, id_):
        self.message_id = id_


class NotAManager(AppCommandError):
    def __init__(self, role_id=None):
        self.role_id = role_id


class RoleNotFound(DiscordException):
    def __init__(self, role_name):
        self.role_name = role_name
