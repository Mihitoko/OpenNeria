import io
import logging
import os
import time
import typing
from datetime import datetime, tzinfo, timedelta, timezone

import discord
import pytz
from aiocache import cached

from persistence.models import Server
from errors.basic import DateConversionError, DateTimeInPast, NumberConversionError, InvalidNumber, RoleNotFound

DATETIME_FORMAT = '%d.%m.%y/%H:%M%z'

logger = logging.getLogger("Neria")

class Missing:
    pass


def scan_cogs() -> typing.List[str]:
    modules = os.listdir("cogs")
    ret = list()
    for module in modules:
        if module.startswith("__"):
            continue
        m = "cogs." + module.replace(".py", "")
        ret.append(m)
    return ret


class CachedQueries:
    @classmethod
    @cached(ttl=10)
    async def fetch_event_presets(cls, server_id):
        server = await Server.get_safe(server_id)
        await server.fetch_event_presets()
        return server.event_presets


def strip_text(text: str):
    pieces = text.split("\n")
    new = []
    for i in pieces:
        new.append(i.strip())
    return "\n".join(new)


def markdown_line_text(text):
    to_mark = strip_text(text).split("\n")
    new = []
    for i in to_mark:
        new.append(f"`{i}`")
    return "\n".join(new)


def parse_datetime(text: str, timedelta_seconds):
    try:
        utc_time: datetime = datetime.strptime(text.strip() + "+00:00", DATETIME_FORMAT)
        utc_time = utc_time.replace(tzinfo=timezone.utc)
        parsed_time = utc_time + timedelta(seconds=timedelta_seconds)
        if parsed_time.timestamp() < datetime.now(tz=timezone.utc).timestamp():
            raise DateTimeInPast(parsed_time)
    except ValueError:
        raise DateConversionError(text)
    return parsed_time


def get_date_time_str(timestamp, offset):
    ret = datetime.fromtimestamp(timestamp, tz=pytz.timezone("UTC")) - timedelta(seconds=offset)
    return ret.strftime("%d.%m.%y/%H:%M")


def parse_num(text: str, min_value=None, max_value=None, cls=int, default=Missing):
    try:
        if len(text) == 0:
            if default == Missing:
                raise ValueError
            else:
                return default
        num = cls(text.replace(",", "."))
    except ValueError:
        raise NumberConversionError(text)

    if (min_value and num < min_value) or (max_value and num > max_value):
        raise InvalidNumber(num)
    return num


def get_roles_from_strings(guild: discord.Guild, string_list: list[str], raise_exc=True):
    ret = []
    for string in string_list:
        try:
            role_id = int(string)
            role = guild.get_role(role_id)
            if not role:
                raise ValueError
            ret.append(role)
        except ValueError:
            role = discord.utils.find(lambda s: s.name.lower() == string.lower(), guild.roles)
            if not role:
                if raise_exc:
                    raise RoleNotFound(string)

            ret.append(role)
    return ret


def parse_list(text: str, seperator=",", strip=True):
    content_list = [i.strip() if strip else i for i in text.split(seperator)]
    if content_list[0] == "":
        return []
    return content_list


def get_message_link(guild, channel, msg_id):
    return f"https://discord.com/channels/{guild}/{channel}/{msg_id}"


def build_fields(embed: discord.Embed, title, to_write, no_value, spacer=True, inline=True):
    s = io.StringIO()
    if len(to_write) == 0:
        embed.add_field(
            name=title,
            value=no_value,
            inline=inline
        )
        return
    for string in to_write:
        if len(s.getvalue()) + len(string) > 1000:
            to_field = s.getvalue()
            s = io.StringIO()
            s.write(string)
            embed.add_field(
                name=title,
                value=to_field,
                inline=inline
            )
            if spacer:
                embed.add_field(name="\u200b", value="\u200b")
        else:
            s.write(string)
    else:
        if len(s.getvalue()) == 0:
            return
        embed.add_field(
            name=title,
            value=s.getvalue(),
            inline=inline
        )


class Cooldown:

    def __init__(self, ttl, maxsize=100):
        self.maxsize = maxsize
        self.ttl = ttl
        self.map = dict()

    def add_item(self, item):
        self.map[item] = time.time()
        if len(self.map) > self.maxsize:
            self.clear()

    def get_remaining(self, item):
        t = self.map[item]
        ret = t - time.time()
        if ret > 0:
            ret = 0
        return self.ttl - round(abs(ret))

    def clear(self):
        to_del = []
        for k, _ in self.map.items():
            if self.can_execute(k):
                to_del.append(k)
        for i in to_del:
            self.map.pop(i)

    def can_execute(self, item):
        i = self.map.get(item, None)
        if i is None:
            return True

        if time.time() - i >= self.ttl:
            return True

        return False


class TimingContext:
    """
    A Context manager Utility to measure execution time
    """

    def __init__(self, name, max_time=1):
        self.name = name
        self.max_time = 1
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        total_time = round(time.perf_counter() - self.start_time, 3)
        logger.debug(f"{self.name} ||| Executed with a total time of {total_time}.")
        if total_time > self.max_time:
            logger.warning(f"{self.name} ||| took to long to execute. Took {total_time} should be less then {self.max_time}"
                           )

