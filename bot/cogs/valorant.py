import os
import aiohttp

from discord import app_commands, Interaction
from discord.ext import commands
from dotenv import load_dotenv

from bot.cogs.utils.valorant import *
from bot.cogs.utils.paginator import Paginator

load_dotenv()

class ValorantAPI:
    BASE = "https://api.henrikdev.xyz/valorant/v2"
    MATCHES = "https://api.henrikdev.xyz/valorant/v3"
    COSMETICS = "https://valorant-api.com/v1"

    def __init__(self):
        self.api_key = os.getenv("VALORANT_API_KEY")
        self.headers = {"Authorization": self.api_key}

    async def fetch_json(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as res:
                return await res.json() if res.status == 200 else None

    async def get_rank(self, name, tag):
        return await self.fetch_json(f"{self.BASE}/mmr/ap/{name}/{tag}")

    async def get_account_by_puuid(self, puuid):
        return await self.fetch_json(f"{self.BASE}/by-puuid/account/{puuid}")

    async def get_recent_matches(self, name, tag):
        return await self.fetch_json(f"{self.MATCHES}/matches/ap/{name}/{tag}?mode=competitive")

    async def get_player_card_icon(self, uuid):
        data = await self.fetch_json(f"{self.COSMETICS}/playercards/{uuid}")
        return data['data']['displayIcon'] if data else None

class Valorant(commands.GroupCog, name='valorant', description='Commands for Valorant Rank and Matches'):
    def __init__(self, bot):
        self.bot = bot
        self.api = ValorantAPI()
        self.api_key = os.getenv('VALORANT_API_KEY')

    @app_commands.command(name='rank', description="View your current Valorant rank, RR, and MMR progress.")
    @app_commands.describe(name='Your Valorant username without the tag', tag='Your Valorant tag without the #')
    async def rank(self, itr: Interaction, name: str, tag: str):
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

        embed = build_rank_embed(name, icon_url, rank_icon, current_rank, current_rr, current_elo, rr_change, peak_rank)
        await itr.followup.send(embed=embed)

    @app_commands.command(name='matches', description="See detailed summaries of your recent Valorant matches.")
    @app_commands.describe(name='Your Valorant username without the tag', tag='Your Valorant tag without the #')
    async def matches(self, itr: Interaction, name: str, tag: str):
        await itr.response.defer()

        matches_data = await self.api.get_recent_matches(name, tag)
        if not matches_data or 'data' not in matches_data:
            return await itr.followup.send('Player not found or no recent matches.', ephemeral=True)

        puuid = matches_data['data'][0]['players']['all_players'][0]['puuid']
        profile = await self.api.get_account_by_puuid(puuid)
        player_card_id = profile['data']['card']
        card_icon = await self.api.get_player_card_icon(player_card_id)

        embeds = []
        for match in matches_data['data']:

            match_data = get_match_data(match, name)
            embed = build_match_embed(name, card_icon, **match_data)
            embeds.append(embed)

        await Paginator(itr, embeds).start()

async def setup(bot):
    await bot.add_cog(Valorant(bot))
