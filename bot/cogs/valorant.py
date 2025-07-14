from typing import TYPE_CHECKING
from io import BytesIO
import os
from typing import List
import aiohttp

from discord import File, app_commands, Interaction
from discord.ext import commands
from dotenv import load_dotenv
from bot.utils.types import Crosshair
from bot.cogs.utils.valorant import get_puuid, get_match_data, build_match_embed, build_rank_embed, add_default_crosshair
from bot.cogs.utils.paginator import Paginator
from bot.cogs.views.valorant import AccountSelectView, LinkAccountModal, CrosshairPaginatorView

load_dotenv()

if TYPE_CHECKING:
    from bot import MyBot


class ValorantAPI:
    BASE = "https://api.henrikdev.xyz/valorant"
    MATCHES = "https://api.henrikdev.xyz/valorant/v3"
    COSMETICS = "https://valorant-api.com/v1"

    def __init__(self):
        self.api_key = os.getenv("VALORANT_API_KEY")
        self.session = aiohttp.ClientSession(headers={"Authorization": self.api_key})

    async def fetch_json(self, url) -> dict:
        res = await self.session.get(url)
        return await res.json() if res.status == 200 else None

    async def fetch_content(self, url):
        res = await self.session.get(url)
        return await res.read() if res.status == 200 else None

    async def get_rank(self, name, tag) -> dict:
        return await self.fetch_json(f"{self.BASE}/v2/mmr/ap/{name}/{tag}")

    async def get_account_by_puuid(self, puuid) -> dict:
        return await self.fetch_json(f"{self.BASE}/v2/by-puuid/account/{puuid}")

    async def get_recent_matches(self, name, tag) -> dict:
        return await self.fetch_json(f"{self.BASE}/v3/matches/ap/{name}/{tag}?mode=competitive&size=10")

    async def get_player_card_icon(self, uuid):
        data = await self.fetch_json(f"{self.COSMETICS}/playercards/{uuid}")
        return data['data']['displayIcon'] if data else None

    async def get_crosshair_from_code(self, code: str):
        return await self.fetch_content(f"{self.BASE}/v1/crosshair/generate?id={code}")


class Valorant(commands.GroupCog, name='valorant', description='Valorant stat tracking, match history, and crosshair management.'):
    def __init__(self, bot: 'MyBot'):
        self.bot = bot
        self.api = ValorantAPI()

    async def get_user_accounts(self, user_id: int):
        rows = await self.bot.db.fetchall(
            "SELECT label, name, tag FROM valorant_profiles WHERE user_id = %s", str(
                user_id)
        )
        return rows

    async def _show_rank(self, itr: Interaction, name: str, tag: str) -> None:
        await itr.response.defer()
        mmr_data = await self.api.get_rank(name, tag)
        if not mmr_data or 'data' not in mmr_data:
            return await itr.followup.send('Player not found', ephemeral=True)

        puuid = mmr_data['data'].get('puuid')
        profile = await self.api.get_account_by_puuid(puuid)
        if not profile:
            return await itr.followup.send('Failed to load profile data.', ephemeral=True)

        card_id = profile['data']['card']
        icon_url = await self.api.get_player_card_icon(card_id)

        current_data = mmr_data['data']['current_data']
        current_rank = current_data['currenttierpatched']
        current_rr = current_data['ranking_in_tier']
        current_elo = current_data['elo']
        rank_icon = current_data['images']['large']
        rr_change = current_data.get('mmr_change_to_last_game', 0)
        rr_change = f"{rr_change:+}"
        peak_rank = mmr_data['data']['highest_rank']['patched_tier']

        embed = build_rank_embed(
            name, icon_url, rank_icon, current_rank, current_rr, current_elo, rr_change, peak_rank)
        await itr.followup.send(embed=embed)

    async def _show_matches(self, itr: Interaction, name: str, tag: str) -> None:
        await itr.response.defer()

        match_history = await self.api.get_recent_matches(name, tag)
        if not match_history or 'data' not in match_history:
            return await itr.followup.send('Player not found or no recent matches.', ephemeral=True)

        puuid = get_puuid(match_history, name)
        profile = await self.api.get_account_by_puuid(puuid)
        card_icon = await self.api.get_player_card_icon(profile['data']['card'])

        embeds = []
        for match in match_history['data']:

            match_data = get_match_data(match, puuid)
            embed = build_match_embed(match_data, card_icon)
            embeds.append(embed)

        await Paginator(itr, embeds).start()

    async def _get_crosshairs(self, db, user_id) -> List[Crosshair]:
        query = "SELECT * FROM valorant_crosshairs WHERE user_id = %s"
        rows = await db.fetchall(query, user_id)

        if not rows:
            await add_default_crosshair(self.bot.db, user_id, self.api)
            rows = await self.bot.db.fetchall(query, user_id)

        crosshairs = []

        for crosshair in rows:
            crosshairs.append(Crosshair(label=crosshair['label'], code=crosshair['code'], image_bytes=crosshair['image']))

        return crosshairs

    @app_commands.command(name='rank', description="View your current Valorant rank, RR, and MMR progress.")
    @app_commands.describe(name='Your Valorant username without the tag', tag='Your Valorant tag without the #')
    async def rank(self, itr: Interaction, name: str = None, tag: str = None):
        if name and tag:
            return await self._show_rank(itr, name, tag)

        accounts = await self.get_user_accounts(itr.user.id)
        if not accounts:
            return await itr.response.send_message("You haven’t linked any accounts yet. Use `/valorant link`.", ephemeral=True)

        if len(accounts) == 1:
            name, tag = accounts[0]['name'], accounts[0]['tag']
            return await self._show_rank(itr, name, tag)

        async def on_account_selected(inter, label):
            for row in accounts:
                if row['label'] == label:
                    name, tag = row['name'], row['tag']
                    return await self._show_rank(inter, name, tag)

        view = AccountSelectView(itr.user.id, accounts, on_account_selected)
        await itr.response.send_message("Select the account to use:", view=view)

    @app_commands.command(name='matches', description="See detailed summaries of your recent Valorant matches.")
    @app_commands.describe(name='Your Valorant username without the tag', tag='Your Valorant tag without the #')
    async def matches(self, itr: Interaction, name: str = None, tag: str = None):
        if name and tag:
            return await self._show_matches(itr, name, tag)

        accounts = await self.get_user_accounts(itr.user.id)
        if not accounts:
            return await itr.response.send_message("You haven’t linked any accounts yet. Use `/valorant link`.", ephemeral=True)

        if len(accounts) == 1:
            name, tag = accounts[0]['name'], accounts[0]['tag']
            return await self._show_matches(itr, name, tag)

        async def on_account_selected(inter, label):
            for row in accounts:
                if row['label'] == label:
                    name, tag = row['name'], row['tag']
                    return await self._show_matches(inter, name, tag)

        view = AccountSelectView(itr.user.id, accounts, on_account_selected)
        await itr.response.send_message("Select the account to use:", view=view)

    @app_commands.command(name='crosshairs', description="Manage your Valorant crosshairs.")
    async def crosshairs(self, itr: Interaction):
        await itr.response.defer(thinking=True)
        crosshairs = await self._get_crosshairs(self.bot.db, itr.user.id)

        view = CrosshairPaginatorView(itr.user, crosshairs, self.bot, self.api)
        crosshair = crosshairs[0]

        file = File(BytesIO(crosshair.image_bytes),filename=f"{crosshair.label}.png")
        await itr.edit_original_response(content=f'Name: `{crosshair.label}`\nCode: `{crosshair.code}`', attachments=[file], view=view)

        await view.wait()
        for child in view.children:
            child.disabled = True

        await itr.edit_original_response(view=view)

    @app_commands.command(name="link", description="Link your valorant profile to your discord account.")
    async def link(self, itr: Interaction):
        await itr.response.send_modal(LinkAccountModal(self.bot, itr.user.id))

    @app_commands.command(name='unlink', description="Unlink your valorant profile connected to you discord account.")
    async def unlink(self, itr: Interaction):
        accounts = await self.get_user_accounts(itr.user.id)

        async def on_account_selected(inter: Interaction, label: str) -> None:
            await self.bot.db.execute("DELETE FROM valorant_profiles WHERE user_id = %s AND label = %s", inter.user.id, label)
            return await inter.edit_original_response(content=f'{label} has been unlinked', view=None)

        view = AccountSelectView(itr.user.id, accounts, on_account_selected)
        await itr.response.send_message("Select the account to unlink:", view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Valorant(bot))
