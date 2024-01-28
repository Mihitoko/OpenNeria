import asyncio
import logging
import subprocess
import sys
import time

import coloredlogs
from tortoise import Tortoise
from bot import Neria
from persistence.models import Event
from utils.config_manager import ConfigManager

ConfigManager.load()
logger = logging.getLogger("Neria")

log_format = "%(name)s[%(process)d] | %(asctime)s,%(msecs)03d | %(levelname)s | %(message)s"

file_hdlr = logging.FileHandler("log.txt")
file_hdlr.setFormatter(logging.Formatter(fmt=log_format))
file_hdlr.setLevel(logging.WARNING)

discord_logger = logging.getLogger("discord")
discord_file_hdlr = logging.FileHandler("discord_log.txt")
discord_file_hdlr.setFormatter(logging.Formatter(fmt=log_format))

logger.handlers.append(file_hdlr)
discord_logger.handlers.append(discord_file_hdlr)

coloredlogs.install("WARNING", logger=discord_logger, fmt=log_format)
coloredlogs.install(ConfigManager.get_setting("loglvl"), logger=logger, fmt=log_format)


def migrate():
    logger.info("Start migrating database")
    pw = ConfigManager.get_secret("db_password")
    usr = ConfigManager.get_secret("db_user")
    db = ConfigManager.get_secret("db_name")
    host = ConfigManager.get_secret("db_host")
    result = subprocess.run(
        [sys.executable, "-m", "yoyo", "apply", "--database", f"postgresql://{usr}:{pw}@{host}/{db}"],
        stdout=sys.stdout)
    if result.returncode != 0:
        raise Exception("DB migrations failed")
    logger.info("Migration finished")


async def init_tortoise():
    logger.info("Creating Database connection...")
    await Tortoise.init(config=ConfigManager.load_tortoise_config())
    x = await Event.all()
    if "create_schemas" in sys.argv:
        logger.info("Creating Database schema...")
        await Tortoise.generate_schemas()


async def run_app(neria: Neria):
    await init_tortoise()
    logger.info("Logging into Discord")
    await neria.login(ConfigManager.get_secret("bot_token"))
    logger.info("Connecting to gateway...")
    await neria.connect(reconnect=True)


if __name__ == '__main__':
    migrate()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = Neria()
    try:
        logger.info(f"Starting Bot on timestamp {time.time()}")
        loop.run_until_complete(run_app(bot))
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected. Terminating bot.")
        pass

    finally:
        loop.run_until_complete(bot.close())
