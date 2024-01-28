import asyncio
import typing

import discord
from discord import Forbidden

from errors.basic import NumberConversionError, DateConversionError, NotAPreset, DateTimeInPast, InvalidNumber, \
    EventNotFound, NotAManager, RoleNotFound
from errors.registration import PlayersFullError, RequirementsNotMetError, NoPrioRoleError
from locales.gen import LanguageSchema


class ErrorCallback:
    def __init__(self, t, cb):
        self.e_instance = None
        self.t = t
        self.cb = cb

    def handle(self, lang, err, interaction):
        return self.cb(self.e_instance, lang, err, interaction)


def handler(t: type[Exception]):
    """
    Register an error string handler
    """
    def wrapper(func):
        return ErrorCallback(t, func)
    return wrapper


class ErrorStringHandler:
    """
    Converts errors to strings that can be used in embeds
    """
    __handler_map__: dict[type[Exception], ErrorCallback] = {}

    def __new__(cls, *args, **kwargs):
        for n, m in cls.__dict__.items():
            if isinstance(m, ErrorCallback):
                cls.__handler_map__[m.t] = m
        return super().__new__(cls)

    def __init__(self):
        for h in self.__handler_map__.values():
            h.e_instance = self

    def get_err_text(self, lang: LanguageSchema.Errors, err: Exception, interaction: discord.Interaction) -> typing.Union[tuple[str, str], None]:
        """
        tries to find the right exception text handler, when it finds one it will be executed
        otherwise it will return none.
        """
        for i in self.__handler_map__.keys():
            if isinstance(err, i):
                return self.__handler_map__.get(i).handle(lang, err, interaction)

        return None

    @handler(NumberConversionError)
    def number_conversion(self, lang: LanguageSchema.Errors, err: NumberConversionError, _) -> tuple[str, str]:
        return lang.number_conversion.title.get_string(), lang.number_conversion.desc.get_string(err.num)

    @handler(DateConversionError)
    def date_conversion(self, lang: LanguageSchema.Errors, err: DateConversionError, _) -> tuple[str, str]:
        return lang.date_conversion.title.get_string(), lang.date_conversion.desc.get_string(err.date_str)

    @handler(NotAPreset)
    def preset_not_found(self, lang: LanguageSchema.Errors, err: NotAPreset, _) -> tuple[str, str]:
        return lang.preset_not_found.title.get_string(), lang.preset_not_found.desc.get_string(err.name)

    @handler(asyncio.TimeoutError)
    def timout(self, lang: LanguageSchema.Errors, _: asyncio.TimeoutError, __) -> tuple[str, str]:
        return lang.timout.title.get_string(), lang.timout.desc.get_string()

    @handler(DateTimeInPast)
    def date_in_past(self, lang: LanguageSchema.Errors, _: DateTimeInPast, __) -> tuple[str, str]:
        return lang.date_past.title.get_string(), lang.date_past.desc.get_string()

    @handler(InvalidNumber)
    def invalid_number(self, lang: LanguageSchema.Errors, _: InvalidNumber, __) -> tuple[str, str]:
        return lang.InvalidNumber.title.get_string(), lang.InvalidNumber.desc.get_string()

    @handler(EventNotFound)
    def event_not_found(self, lang: LanguageSchema.Errors, _: EventNotFound, __) -> tuple[str, str]:
        return lang.event_not_found.title.get_string(), lang.event_not_found.desc.get_string()

    @handler(NotAManager)
    def not_manager(self, lang: LanguageSchema.Errors, err: NotAManager, interaction: discord.Interaction) -> tuple[str, str]:
        header = lang.not_manager.title.get_string()
        if err.role_id:
            description = lang.not_manager.desc.get_string(interaction.guild.get_role(err.role_id).mention)
        else:
            description = lang.not_manager.desc_no_role.get_string()

        return header, description

    @handler(Forbidden)
    def forbidden(self, lang: LanguageSchema.Errors, *_) -> tuple[str, str]:
        return lang.forbidden.title.get_string(), lang.forbidden.desc.get_string()

    @handler(PlayersFullError)
    def lfg_full(self, lang: LanguageSchema.Errors, *_) -> tuple[str, str]:
        return lang.lfg_full.title.get_string(), lang.lfg_full.desc.get_string()

    @handler(RequirementsNotMetError)
    def to_weak(self, lang: LanguageSchema.Errors, *_) -> tuple[str, str]:
        return lang.lfg_req_not_met.title.get_string(), lang.lfg_req_not_met.desc.get_string()

    @handler(NoPrioRoleError)
    def no_prio_role(self, lang: LanguageSchema.Errors, err: NoPrioRoleError, *_) -> tuple[str, str]:
        return (lang.no_prio_role.title.get_string(),
                lang.no_prio_role.desc.get_string(', '.join([i.mention for i in err.roles]), str(int(err.ignored_in))))

    @handler(RoleNotFound)
    def lfg_full(self, lang: LanguageSchema.Errors, err: RoleNotFound, *_) -> tuple[str, str]:
        return lang.role_not_found.title.get_string(), lang.role_not_found.desc.get_string(err.role_name)
