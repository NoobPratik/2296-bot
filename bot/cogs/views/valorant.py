from io import BytesIO
from typing import List
import discord
from discord.ui import Modal, TextInput, View, Select, Button, button
from discord import ButtonStyle, File, Interaction, SelectOption, User
from bot.utils.types import Crosshair

class LinkAccountModal(Modal, title="Link Valorant Account"):
    label = TextInput(label="Label (e.g. main, alt, tenz)", placeholder="unique name", required=True)
    username = TextInput(label="Username", placeholder="Riot ID username", required=True)
    tag = TextInput(label="Tag", placeholder="e.g. 1234 or NA1", required=True)

    def __init__(self, bot, user_id):
        super().__init__()
        self.bot = bot
        self.user_id = user_id

    async def on_submit(self, interaction: Interaction):
        query = """
        INSERT INTO valorant_profiles (user_id, label, name, tag)
        VALUES (%s, %s, %s, %s) AS new
        ON DUPLICATE KEY UPDATE
            name = new.name,
            tag = new.tag
        """
        await self.bot.db.execute(query, str(self.user_id), self.label.value, self.username.value, self.tag.value)
        await interaction.response.send_message(
            f"✅ Linked account `{self.label.value}` as `{self.username.value}#{self.tag.value}`!",
            ephemeral=True
        )


class AccountSelectView(View):
    def __init__(self, user_id, accounts, callback):
        super().__init__(timeout=30)
        self.callback_fn = callback

        options = [
            discord.SelectOption(label=account['label'], description=f"{account['name']}#{account['tag']}")
            for account in accounts
        ]

        self.select = Select(placeholder="Choose a Valorant account", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

        self.user_id = user_id
        self.accounts = accounts

    async def select_callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("You're not allowed to use this selection.", ephemeral=True)

        selected_label = self.select.values[0]
        await self.callback_fn(interaction, selected_label)
        self.stop()


class CrosshairPageSelect(Select):
    def __init__(self, pages: List[Crosshair]):
        options = [SelectOption(label=f"{pages[i].label}", value=str(i)) for i in range(len(pages))]
        super().__init__(placeholder="Jump to crosshair", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: Interaction):
        self.view.current_page = int(self.values[0])
        await self.view.update_page(interaction)


class CrosshairPaginatorView(View):
    def __init__(self, author: User, pages: List[Crosshair], bot, api):
        super().__init__(timeout=120)
        self.author = author
        self.pages = pages
        self.current_page = 0
        self.bot = bot
        self.api = api
        self.add_item(CrosshairPageSelect(self.pages))
        self.update_buttons()

    def update_buttons(self):
        self.page_label.label = f"{self.current_page + 1}/{len(self.pages)}"
        self.prev_button.disabled = self.current_page <= 0
        self.next_button.disabled = self.current_page >= len(self.pages) - 1
        self.delete_button.disabled = len(self.pages) <= 1

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.author.id
    
    async def reload_crosshairs(self, interaction: Interaction):
        rows = await self.bot.db.fetchall("SELECT * FROM valorant_crosshairs WHERE user_id = %s", self.author.id)
        self.pages.clear()
        for row in rows:
            image_bytes = await self.api.get_crosshair_from_code(row['code'])
            self.pages.append(Crosshair(label=row['label'], code=row['code'], file_bytes=image_bytes))

        self.current_page = max(0, min(self.current_page, len(self.pages) - 1))
        for item in self.children:
            if isinstance(item, CrosshairPageSelect):
                self.remove_item(item)
        self.add_item(CrosshairPageSelect(self.pages))

        await self.update_page(interaction)

    async def update_page(self, interaction: Interaction):
        self.update_buttons()
        crosshair = self.pages[self.current_page]
        file = File(BytesIO(crosshair.file_bytes), filename=f"{crosshair.label}.png")
        await interaction.response.edit_message(content=f'Name: `{crosshair.label}`\nCode: `{crosshair.code}`', attachments=[file], view=self)

    @button(label="➕", style=ButtonStyle.success, row=0)
    async def add_button(self, interaction: Interaction, _: Button):
        await interaction.response.send_modal(AddCrosshairModal(self.author.id, self.bot.db, self))

    @button(label="◀️", style=ButtonStyle.primary, row=0)
    async def prev_button(self, interaction: Interaction, _: Button):
        self.current_page -= 1
        await self.update_page(interaction)

    @button(label="1/1", style=ButtonStyle.secondary, disabled=True, row=0)
    async def page_label(self, _: Interaction, __: Button):
        pass

    @button(label="▶️", style=ButtonStyle.primary, row=0)
    async def next_button(self, interaction: Interaction, _: Button):
        self.current_page += 1
        await self.update_page(interaction)

    @button(label="🗑️", style=ButtonStyle.danger, row=0)
    async def delete_button(self, interaction: Interaction, _: Button):
        if len(self.pages) <= 1:
            await interaction.response.send_message("You must have at least one crosshair.", ephemeral=True)
            return

        label = self.pages[self.current_page].label
        await self.bot.db.execute(
            "DELETE FROM valorant_crosshairs WHERE user_id = %s AND label = %s",
            self.author.id, label
        )
        await interaction.response.send_message(f"Deleted **{label}**", ephemeral=True)

        await self.reload_crosshairs(interaction)

class AddCrosshairModal(discord.ui.Modal, title="Add Crosshair"):
    label = discord.ui.TextInput(label="Label")
    code = discord.ui.TextInput(label="Crosshair Code")

    def __init__(self, user_id, db, view):
        super().__init__()
        self.user_id = user_id
        self.db = db
        self.view = view

    async def on_submit(self, interaction: Interaction):
        await self.db.execute(
            "INSERT INTO valorant_crosshairs (user_id, label, code) VALUES (%s, %s, %s)",
            self.user_id, self.label.value, self.code.value
        )
        await self.view.reload_crosshairs(interaction)


class EditCrosshairModal(discord.ui.Modal, title="Edit Crosshair"):
    label = discord.ui.TextInput(label="Label", required=False)
    code = discord.ui.TextInput(label="Crosshair Code", required=False)

    def __init__(self, user_id, db, view, crosshair):
        super().__init__()
        self.user_id = user_id
        self.db = db
        self.view = view
        self.crosshair = crosshair

    async def on_submit(self, interaction: Interaction):
        new_label = self.label.value or self.crosshair['label']
        new_code = self.code.value or self.crosshair['code']
        await self.db.execute(
            "UPDATE valorant_crosshairs SET label = %s, code = %s WHERE user_id = %s AND code = %s",
            new_label, new_code, self.user_id, self.crosshair['code']
        )
        await interaction.response.send_message("Crosshair updated!", ephemeral=True)