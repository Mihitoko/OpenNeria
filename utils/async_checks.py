from discord.app_commands import check
import discord

from persistence.models import Server
from errors.basic import NotAManager


def has_manager_permission():
    async def actual_check(interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        server = await Server.get_safe(interaction.guild.id)
        role_id = server.manager_role
        actual_role = interaction.guild.get_role(role_id)
        if actual_role:
            if actual_role in interaction.user.roles:
                return True
        raise NotAManager(role_id)
    return check(actual_check)
