import discord.errors


class PlayersFullError(discord.errors.DiscordException):
    def __init__(self, max_):
        self.max_players = max_


class RequirementsNotMetError(discord.errors.DiscordException):
    pass


class NoPrioRoleError(discord.errors.DiscordException):
    def __init__(self, roles, ignored_id):
        self.roles = roles
        self.ignored_in = ignored_id
