import discord

from utils.utils import CachedQueries


class AutoCompleteCallbacks:

    @classmethod
    async def query_presets(cls, interaction: discord.Interaction, current: str):
        presets = await CachedQueries.fetch_event_presets(interaction.guild.id)
        ret = [discord.app_commands.Choice(name=i.name, value=i.name) for i in presets if i.name.startswith(current)]
        ret.sort(key=lambda i: i.name)
        if len(ret) > 25:
            ret = ret[:25]
        return ret
