from tortoise.exceptions import DoesNotExist
from tortoise.models import Model
from tortoise import fields
from tortoise.fields import data

from persistence import EventStates
from persistence.db_fields import PydanticDBField
from persistence.pydantic_models import AdvancedOptions
from utils.static import PlayerClass, StaticIdMaps


class EvenDatatMeta:
    title: str = fields.TextField()
    description: str = fields.TextField(default="")
    max_players: int = fields.SmallIntField()
    advanced_settings: AdvancedOptions = PydanticDBField(null=True)


class Event(EvenDatatMeta, Model):
    id: int
    creator: "Users" = fields.ForeignKeyField("models.Users", "created_events")
    server: "Server" = fields.ForeignKeyField("models.Server", "all_events")
    registered_users: tuple["EventRegister"] = fields.ReverseRelation["EventRegister"]
    event_start: int = data.BigIntField()
    channel_id: int = fields.BigIntField()
    message_id: int = fields.BigIntField(unique=True)
    weekly: bool = fields.BooleanField(default=False)
    last_dispatch: int = fields.BigIntField(null=True)
    guild_event_id: int = fields.BigIntField(unique=True, null=True)
    state: int = fields.SmallIntField(null=False, default=False)

    async def fetch_participants(self, include_users=False):
        if include_users:
            await self.fetch_related("registered_users__user", "registered_users__character")
        else:
            await self.fetch_related("registered_users")

    async def fetch_server(self):
        await self.fetch_related("server")

    async def fetch_creator(self):
        await self.fetch_related("creator")

    def get_msg_link(self, guild_id):
        return f"https://discord.com/channels/{guild_id}/{self.channel_id}/{self.message_id}"

    @property
    def registered_count(self):
        counter = 0
        for i in self.registered_users:
            if not i.substitute:
                counter += 1
        return counter

    @property
    def has_ended(self):
        return self.state is EventStates.ENDED


class EventRegister(Model):
    event: "Event" = fields.ForeignKeyField("models.Event", "registered_users")
    user: "Users" = fields.ForeignKeyField("models.Users", "registered_for")
    character: "PlayerCharacter" = fields.ForeignKeyField("models.PlayerCharacter")
    substitute: bool = fields.BooleanField(default=False)
    registered_at: int = fields.BigIntField()
    notified: bool = fields.BooleanField(default=False, null=False)
    notify_before: int = fields.IntField(null=False, default=300)

    async def fetch_character(self):
        await self.fetch_related("character")


class PlayerCharacter(Model):
    id: int
    class_type: int = fields.SmallIntField()
    character_name: str = fields.TextField(max_length=20)
    item_lvl: int = fields.BigIntField()
    user: "Users" = fields.ForeignKeyField("models.Users", "characters")
    api_id: int = fields.IntField(null=True)

    @property
    def character_class(self) -> PlayerClass:
        return StaticIdMaps.PLAYER_CLASSES[self.class_type]

    @property
    def is_primary(self):
        return self.id == self.user.main_class


class Users(Model):
    id = fields.BigIntField(pk=True)
    created_events = fields.ReverseRelation["Event"]
    characters: tuple["PlayerCharacter"] = fields.ReverseRelation["PlayerCharacter"]
    registered_for: tuple["EventRegister"] = fields.ReverseRelation["EventRegister"]
    main_class = fields.IntField(null=True)
    notify_before = fields.BigIntField(null=False, default=300)
    twitch_id: str = fields.TextField(null=True)

    async def fetch_characters(self):
        await self.fetch_related("characters")

    async def fetch_registered_events(self):
        await self.fetch_related("registered_for__event")

    @classmethod
    async def get_safe(cls, i):
        try:
            ret = await cls.get(id=i)
        except DoesNotExist:
            ret = await cls.create(id=i)
        return ret

    def get_primary(self):
        for i in self.characters:
            if i.is_primary:
                return i


class Server(Model):
    id = fields.BigIntField(pk=True)
    lang = fields.TextField(default="en")
    all_events: tuple["Event"] = fields.ReverseRelation["Event"]
    event_presets: tuple["EventPreset"] = fields.ReverseRelation["EventPreset"]
    role_assign = fields.BooleanField(default=False)
    event_creator_role_id = fields.BigIntField(null=True)
    manager_role: int = fields.BigIntField(null=True)
    time_offset: int = fields.IntField(default=0)
    delete_delay: int = fields.SmallIntField(default=-1)
    log_channel: int = fields.BigIntField(default=None, null=True)

    def offset_hours(self):
        if self.time_offset == 0:
            return 0
        return int((self.time_offset / 3600) * -1)  # Revert Hours

    @classmethod
    async def get_safe(cls, i):
        try:
            ret = await cls.get(id=i)
        except DoesNotExist:
            ret = await cls.create(id=i)
        return ret

    async def fetch_event_presets(self):
        await self.fetch_related("event_presets")

    def fetch_active_events(self):
        return Event.filter(server_id=self.id, state=EventStates.PLANING)

    @property
    def active_events(self):
        return [i for i in self.all_events if i.state is EventStates.PLANING]


class EventPreset(EvenDatatMeta, Model):
    id: int
    server: "Server" = fields.ForeignKeyField("models.Server", "event_presets")
    name: str = fields.TextField()
    partial: bool = fields.BooleanField(default=False)
    title: str = fields.TextField(null=True)
    description: str = fields.TextField(null=True)
    max_players: int = fields.SmallIntField(null=True)


class MessageDeleteQueue(Model):
    id: int = fields.BigIntField(null=False, pk=True)
    delete_at = fields.BigIntField(null=False)
    channel_id = fields.BigIntField(null=False)
