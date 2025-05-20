from aiohttp import ClientResponseError
from discord import Interaction, app_commands
from discord.app_commands import Group
from discord.ext.commands import GroupCog
from locales.gen import LanguageSchema

from bot import Neria
from persistence.models import Server, Users, PlayerCharacter
from ui.modals.settings_modals import CharacterCreateModal
from ui.views.selects import CharactersSelectView, ClassesSelectView
from utils.overwrites import BetterEmbed, LangAvailable
from utils.static import StaticIdMaps, PlayerClass, MainClasses, ClassRepresentation


class AccountManager(GroupCog, LangAvailable, group_name="character", group_description='Manage your account'):
    sync_group = Group(name="api_sync", description="Sync characters with lost ark",
                       guild_ids=[512660008694186005, 941701979061772298, 532305660369567745])

    def __init__(self, bot: Neria):
        self.bot: Neria = bot

    def get_lang(self, lang: str) -> LanguageSchema.Commands.Characters:
        return self.get_lang_by_reference(lang, LanguageSchema.Commands.Characters)

    @app_commands.command(description="Register a character")
    async def register(self, interaction: Interaction):
        server = await Server.get_safe(interaction.guild.id)
        user = await Users.get_safe(interaction.user.id)
        await user.fetch_characters()
        lang = self.get_lang(server.lang).Register

        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_default_thumbnail()
        embed.set_header(lang.main_class_title.get_string())
        if len(user.characters) == 0:
            embed.description = lang.main_class_desc_first.get_string()
        else:
            embed.description = lang.main_class_desc.get_string()
        embed.footer_from_interaction(interaction)

        main_classes = MainClasses.get_all_classes()
        select = ClassesSelectView(interaction.user, to_choose=main_classes)
        await interaction.response.send_message(embed=embed, view=select, ephemeral=True)
        clazz: ClassRepresentation
        interaction, clazz = await select.get_result()

        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_default_thumbnail()
        embed.set_header(lang.title.get_string())
        embed.footer_from_interaction(interaction)
        embed.description = lang.desc.get_string()
        choose_from = [c for c in StaticIdMaps.PLAYER_CLASSES if c.main_class.class_id == clazz.class_id]
        choose_from.sort(key=lambda item: item.name)
        select = ClassesSelectView(interaction.user, to_choose=choose_from)
        await interaction.response.edit_message(embed=embed, view=select)
        interaction, clazz = await select.get_result()
        modal = CharacterCreateModal(title=lang.modal_title.get_string(), lang=server.lang)
        await interaction.response.send_modal(modal)
        interaction, result = await modal.get_result()
        character = await PlayerCharacter.create(
            **result,
            class_type=clazz.class_id,
            user=user
        )
        if clazz.name == "Bard":
            desc = lang.bard_special.get_string(character.character_name)
        else:
            desc = lang.fin.get_string(character.character_name, clazz.name, character.item_lvl)
        embed.description = desc
        embed.change_type(BetterEmbed.OK)
        await interaction.response.edit_message(embed=embed, view=None)

    @app_commands.command(description="Edit a character")
    async def edit(self, interaction: Interaction):
        server = await Server.get_safe(interaction.guild.id)
        user = await Users.get_safe(interaction.user.id)
        await user.fetch_characters()
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_default_thumbnail()
        embed.footer_from_interaction(interaction)
        lang = self.get_lang(server.lang).Edit
        if len(user.characters) == 0:
            embed.change_type(BetterEmbed.INFO)
            embed.set_header(lang.title_no_char.get_string())
            embed.description = lang.no_char_desc.get_string()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed.set_header(lang.title.get_string())
        embed.description = lang.edit_desc.get_string()
        view = CharactersSelectView(interaction.user, user.characters)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        interaction, character = await view.get_result()
        modal = CharacterCreateModal(character=character, title=lang.modal_title.get_string(), lang=server.lang)
        await interaction.response.send_modal(modal)
        modal_interact: Interaction
        modal_interact, result = await modal.get_result()
        character.character_name = result["character_name"]
        character.item_lvl = result["item_lvl"]
        await character.save()
        embed.change_type(BetterEmbed.OK)
        embed.set_header(lang.edited_title.get_string())
        embed.description = lang.edit_complete.get_string(character.character_name)
        await modal_interact.response.edit_message(embed=embed, view=None)

    @app_commands.command(description="Delete a character")
    async def delete(self, interaction: Interaction):
        server = await Server.get_safe(interaction.guild.id)
        lang = self.get_lang(server.lang).Delete
        user = await Users.get_safe(interaction.user.id)
        await user.fetch_characters()
        embed = BetterEmbed(BetterEmbed.DEFAULT)
        embed.set_default_thumbnail()
        embed.footer_from_interaction(interaction)
        if len(user.characters) == 0:
            embed.change_type(BetterEmbed.INFO)
            embed.set_header(lang.title_no_char.get_string())
            embed.description = lang.no_char_desc.get_string()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed.set_header(lang.title.get_string())
        embed.description = lang.desc.get_string()
        view = CharactersSelectView(interaction.user, to_choose=user.characters)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        interaction, character = await view.get_result()
        embed.set_header(lang.deleted_title.get_string(character.character_name))
        embed.description = lang.deleted_desc.get_string(character.character_name)
        embed.change_type(BetterEmbed.ERROR)
        await character.delete()
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: Neria):
    await bot.add_cog(AccountManager(bot))
