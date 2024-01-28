import typing

import discord


class ContextInterface:
    """
    A special class that interfaces a member and a context.
    This ensures that both entity's can be accessed with the same attributes
    """

    def __init__(self, entity: typing.Union[discord.Interaction]):
        self.entity = entity

    @property
    def guild(self):
        return self.entity.guild

    @property
    def author(self):
        return self.entity.user

    @property
    def command_name(self):
        return None

    @property
    def interaction(self):
        return self.entity

    @property
    def channel(self):
        return self.entity.channel

    @property
    def bot(self):
        return self.entity.client
