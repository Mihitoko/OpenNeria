import json
import random


class MediaManager:
    MEDIA: dict

    @classmethod
    def get_all(cls):
        return cls.MEDIA

    @classmethod
    def save(cls):
        with open("resources/media.json", "w") as file:
            json.dump(cls.MEDIA, file, indent=2)

    @classmethod
    def get_emoji(cls, key: str):
        return cls.MEDIA["emojis"][key.lower()]

    @classmethod
    def get_icon(cls, key: str):
        return cls.MEDIA["icons"][key]

    @classmethod
    def get_thumbnail_rand(cls):
        x = cls.MEDIA["nail"]
        ret = random.choice(x)
        return ret

    @classmethod
    def get_color(cls, t: str) -> hex:
        r = cls.MEDIA["colors"][t]
        if type(r) is list:
            if len(r) == 0:
                raise RuntimeError("Empty color list")
            length = len(r)
            index = random.randint(0, length - 1)
            return int(r[index], base=16)
        return int(r, base=16)

    @classmethod
    def get_color_from_map(cls, index):
        return cls.MEDIA["colors"]["color_map"][index]

    @classmethod
    def get_chart_template(cls, t):
        return cls.MEDIA["chart_templates"][t].copy()

    @classmethod
    def load(cls):
        with open("resources/media.json", "r") as file:
            cls.MEDIA = json.load(file)

    @classmethod
    def reload(cls):
        cls.load()


MediaManager.load()
