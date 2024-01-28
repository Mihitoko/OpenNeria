import logging
from typing import Optional

import aiohttp
from locales.gen import LanguageSchema
from tortoise import connections as tortoise_connections

from bot import Neria
from persistence.models import Users
from utils.config_manager import ConfigManager
from utils.media_manager import MediaManager
from utils.overwrites import ExtCog
from utils.static import StaticIdMaps

logger = logging.getLogger("Neria")


class StatManagement(ExtCog):

    def __init__(self, bot: Neria):
        self.bot: Neria = bot
        self.stats = BotStats()
        if not self.bot.is_debug():
            self.bot.scheduler.scheduler.register("stat_grabber", self.fetch_stats, 600)
        if ConfigManager.get_setting("top_gg"):
            self.bot.scheduler.scheduler.register("top_gg_updater", self.top_gg_poster, 3600)

    def get_lang(self, lang: str) -> LanguageSchema.Commands.settings:
        pass

    async def top_gg_poster(self):
        await self.bot.wait_until_ready()
        async with aiohttp.ClientSession() as session:
            result = await session.post(f"https://top.gg/api/bots/{self.bot.user.id}/stats", headers={
                "Authorization": ConfigManager.get_secret("top_gg")
            }, json=self.stats.get_top_gg_body())

            if not result.ok:
                logger.error(f"Top.gg stat update failed with exit code {result.status}")
                return
            logger.debug(f"Posted stats to top.gg response status: {result.status}")

    async def fetch_stats(self):
        await self.bot.wait_until_ready()
        self.stats.guild_count = len(self.bot.guilds)
        #  Use manual SQL because is easier than using the ORM for this task
        result = await (tortoise_connections.get("main")
                        .execute_query
                        ("""SELECT class_type, count(*) AS count FROM playercharacter 
                                        GROUP BY class_type ORDER BY count DESC"""))
        rows = result[1]
        labels = []
        dataset_values = []
        for row in rows:
            labels.append(StaticIdMaps.PLAYER_CLASSES[row.get("class_type")].name)
            dataset_values.append((MediaManager.get_color_from_map(row.get("class_type")), row.get("count")))
        self.stats.character_labels = labels
        self.stats.character_count = dataset_values
        self.stats.total_characters = sum(i[1] for i in dataset_values)
        self.stats.user_count = await Users.all().count()
        await self.stats.update_chart()


class BotStats:
    def __init__(self):
        self.character_stats_url: Optional[str] = None
        self.total_characters: Optional[int] = None
        self.guild_count: Optional[int] = None
        self.character_labels: list[str] = []
        self.character_count: list[tuple[str, int]] = []
        self.user_count: Optional[int] = None

    async def update_chart(self):
        big_chunks = []
        labels = []
        low_numbers = 0
        c = 0
        for label, char_data in zip(self.character_labels, self.character_count):
            if (char_data[1] / self.total_characters) <= 0.02 or c > 11:
                low_numbers += char_data[1]
            else:
                big_chunks.append(char_data)
                labels.append(label)
                c += 1
        if low_numbers > 0:
            big_chunks.append(("#808080", low_numbers))
            labels.append("Other")

        chart_post = MediaManager.get_chart_template("character_distribution")
        chart_post["chart"]["data"]["labels"] = labels
        chart_post["chart"]["data"]["datasets"][0]["backgroundColor"] = [i[0] for i in big_chunks]
        chart_post["chart"]["data"]["datasets"][0]["data"] = [i[1] for i in big_chunks]
        async with aiohttp.ClientSession() as session:
            result = await session.post("https://quickchart.io/chart/create", json=chart_post)
            json_result = await result.json()
            if json_result["success"]:
                self.character_stats_url = json_result["url"]

    def get_top_gg_body(self):
        return {"server_count": self.guild_count}


async def setup(bot: Neria):
    await bot.add_cog(StatManagement(bot))
