import json
import typing
import os

os.environ.setdefault("NERIA_CONFIG_PATH", "")


class ConfigManager:
    SECRETS: dict
    SETTINGS: dict
    CONFIG_BASE_PATH = os.environ["NERIA_CONFIG_PATH"]

    _is_loaded = False

    @classmethod
    def get_secret(cls, key: str) -> typing.Union[int, str]:
        res = cls.SECRETS[key]
        return res

    @classmethod
    def get_setting(cls, key: str) -> typing.Any:
        res = cls.SETTINGS[key]
        return res

    @classmethod
    def get_setting_default(cls, key, default):
        try:
            return cls.get_setting(key)
        except KeyError:
            return default

    @classmethod
    def load_tortoise_config(cls) -> dict:
        with open(cls.CONFIG_BASE_PATH + "tortoise.json", "r") as file:
            data = json.load(file)
        login_info = data["connections"]["main"]["credentials"]
        login_info["host"] = cls.get_secret("db_host")
        login_info["password"] = cls.get_secret("db_password")
        login_info["database"] = cls.get_secret("db_name")
        login_info["user"] = cls.get_secret("db_user")
        return data

    @classmethod
    def load(cls, force=False):
        if cls._is_loaded and not force:
            return
        with open(cls.CONFIG_BASE_PATH + "secrets.json", "r") as file:
            cls.SECRETS = json.load(file)

        with open(cls.CONFIG_BASE_PATH + "settings.json", "r") as file:
            cls.SETTINGS = json.load(file)

    @classmethod
    def get_debug_guild_when_debug(cls) -> typing.Union[list, None]:
        if cls.get_setting("debug"):
            return cls.get_setting("debug_guilds")
        return None

    @classmethod
    def reload(cls):
        """
        Force reload Configuration
        :return:
        """
        cls.load(force=True)
