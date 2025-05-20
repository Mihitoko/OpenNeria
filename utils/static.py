class ClassRepresentation:
    def __init__(self, name: str, class_id: int, emoji_name: str):
        self.name = name
        self.class_id = class_id
        self.emoji_name = emoji_name

class PlayerClass(ClassRepresentation):
    def __init__(self, name: str, class_id, main_class: ClassRepresentation, emoji_id: int = None, tags=None, emoji_name=None):
        e_name = emoji_name
        if e_name is None:
            e_name = name.lower()
        super().__init__(name, class_id, e_name)

        self.main_class = main_class
        self.emoji_id = emoji_id
        if tags is None:
            self.tags = []
        else:
            self.tags = tags

    def has_tag(self, tag: str):
        return tag in self.tags

class MainClasses:
    MAGE = ClassRepresentation("Mage", 0, 'mage')
    GUNNER = ClassRepresentation("Gunner", 1, 'gunner')
    MARSHALL_ARTIST = ClassRepresentation("Martial Artist", 2, 'martial_artist')
    WARRIOR = ClassRepresentation("Warrior", 3, 'warrior')
    ASSASSIN = ClassRepresentation("Assassin", 4, 'assassin')
    SPECIALIST = ClassRepresentation("Specialist", 5, 'specialist')

    @classmethod
    def get_all_classes(cls):
        return [cls.MAGE, cls.GUNNER, cls.MARSHALL_ARTIST, cls.WARRIOR, cls.ASSASSIN, cls.SPECIALIST]


class StaticIdMaps:

    PLAYER_CLASSES = [
        PlayerClass("Bard", 0, MainClasses.MAGE, tags=["support"]),
        PlayerClass("Sorceress", 1, MainClasses.MAGE),

        PlayerClass("Deadeye", 2, MainClasses.GUNNER),
        PlayerClass("Gunslinger", 3, MainClasses.GUNNER),
        PlayerClass("Sharpshooter", 4, MainClasses.GUNNER),
        PlayerClass("Artillerist", 5, MainClasses.GUNNER),

        PlayerClass("Scrapper", 6, MainClasses.MARSHALL_ARTIST),
        PlayerClass("Soulfist", 7, MainClasses.MARSHALL_ARTIST),
        PlayerClass("Wardancer", 8, MainClasses.MARSHALL_ARTIST),
        PlayerClass("Striker", 9, MainClasses.MARSHALL_ARTIST),

        PlayerClass("Berserker", 10, MainClasses.WARRIOR),
        PlayerClass("Paladin", 11, MainClasses.WARRIOR, tags=["support"]),
        PlayerClass("Gunlancer", 12, MainClasses.WARRIOR),

        PlayerClass("Deathblade", 13, MainClasses.ASSASSIN),
        PlayerClass("Shadowhunter", 14, MainClasses.ASSASSIN),

        # Newly added
        PlayerClass("Glaivier", 15, MainClasses.MARSHALL_ARTIST),

        PlayerClass("Destroyer", 16, MainClasses.WARRIOR),
        PlayerClass("Machinist", 17, MainClasses.GUNNER, emoji_name="scouter"),
        PlayerClass("Summoner", 18, MainClasses.MAGE),
        PlayerClass("Arcana", 19, MainClasses.MAGE),
        PlayerClass("Reaper", 20, MainClasses.ASSASSIN),
        PlayerClass("Artist", 21, MainClasses.SPECIALIST, tags=["support"]),
        PlayerClass("Aeromancer", 22, MainClasses.SPECIALIST),
        PlayerClass("Slayer", 23, MainClasses.WARRIOR),
        PlayerClass("Soul eater", 24, MainClasses.ASSASSIN, emoji_name="souleater")
    ]
    DELETE_DELAYS = [
        900, 1800, 3600, 10800, 43200, 86400
    ]
    DELAY_STRINGS = {
        -1: "never",
        0: "after 15 minutes",
        1: "after 30 minutes",
        2: "after one hour",
        3: "after 3 hours",
        4: "after 12 hours",
        5: "after 1 day"
    }


class DeleteTimeEnum:
    NEVER = -1
    FIFTEEN_MINUTES = 0
    HALF_HOUR = 1
    ONE_HOUR = 2
    THREE_HOURS = 3
    TWELVE_HOURS = 4
    ONE_DAY = 5
