from datetime import datetime
from functools import partial
import random
from discord import Embed, Interaction
import discord
from discord.app_commands import Choice, command, describe, autocomplete
from discord.ext.commands import GroupCog
from typing import TYPE_CHECKING, Literal

import pytz
import requests
from bot.cogs.utils.anime import *
from bot.cogs.utils.paginator import Paginator
from discord.ext import commands
from bot.cogs.views.anime import ConfirmUnfollowView, ScheduleAnimeSelect

if TYPE_CHECKING:
    from bot.bot import MyBot


class Anime(GroupCog, name='anime',description='Search, follow, and explore anime info and schedules.'):
    def __init__(self, bot: 'MyBot'):
        super().__init__()
        self.bot = bot
        self.anime_airing_times = {}

        self.bot.scheduler.add_job(
            anime_remainder_schedule,
            trigger="cron",
            day_of_week="mon",
            args=[self.bot],
            hour=0,
            minute=0,
        )

    @commands.Cog.listener()
    async def on_ready(self):
        self.anime_airing_times = await anime_remainder_schedule(self.bot)

    @command(name='search', description='Search for anime titles and view details.')
    async def search(self, itr: discord.Interaction, anime_name: str):
        await itr.response.defer()
        results = await jikan_search_anime(anime_name)

        if not results:
            return await itr.followup.send(f"No results found for **{anime_name}**", ephemeral=True)

        pages = []
        for anime in results:
            embed = discord.Embed(
                title=anime['title'],
                url=anime['url'],
                description=anime.get('synopsis', 'No synopsis available').replace('[Written by MAL Rewrite]', '').strip(),
                colour=0x7F00FF
            )

            embed.set_thumbnail(url=anime.get('images', {}).get('jpg', {}).get('image_url'))
            embed.add_field(name="Type", value=anime.get('type', 'N/A'), inline=True)
            embed.add_field(name="Status", value=anime.get('status', 'N/A'), inline=True)
            embed.add_field(name="Score", value=f"{anime.get('score', 'N/A')} ({anime.get('scored_by', 0):,} votes)", inline=True)

            embed.add_field(name="Episodes", value=anime.get('episodes', 'N/A'), inline=True)
            embed.add_field(name="Duration", value=anime.get('duration', 'N/A'), inline=True)
            embed.add_field(name="Rank", value=f"#{anime.get('rank', 'N/A')}", inline=True)

            embed.add_field(name="Season", value=anime.get('season', 'N/A').title() if anime.get('season') else "N/A", inline=True)
            embed.add_field(name="Year", value=str(anime.get('year', 'N/A')), inline=True)

            studios = ", ".join([studio["name"] for studio in anime.get("studios", [])]) or "N/A"
            embed.add_field(name="Studios", value=studios, inline=True)

            pages.append(embed)

        paginator = Paginator(itr, pages)
        await paginator.start(quick_navigation=True)

    @command(name='top', description='Browse the top-rated anime by score and popularity.')
    @describe(filter="Filter top anime by this criteria.",type="Type of anime to display.")
    @commands.max_concurrency(1, wait=True)
    async def top(
        self,
        itr: discord.Interaction,
        filter: Literal["airing", "upcoming", "bypopularity", "favorite"] = None,
        type: Literal["tv", "movie"] = None
    ):
        await itr.response.defer()

        initial_pages = await fetch_top_anime_page(page=1, type=type, filter=filter)
        if not initial_pages:
            return await itr.followup.send("Failed to fetch top anime.", ephemeral=True)

        paginator = Paginator(
            itr=itr,
            pages=initial_pages,
            next_page_callback=partial(fetch_top_anime_page, type=type, filter=filter),
            limited=False
        )
        await paginator.start(quick_navigation=False)

    @command(name="schedule", description="View airing anime by weekday schedule.")
    async def schedule(self, itr: discord.Interaction):
        await itr.response.defer()
        tz = pytz.timezone('Asia/Calcutta')
        current_time = datetime.now(tz)
        day_of_week = current_time.strftime('%A')

        r = requests.get('https://subsplease.org/api/?f=schedule&tz=Asia/Calcutta')
        schedule = r.json()['schedule']
        view = ScheduleAnimeSelect(self.bot, schedule, day_of_week)

        embed = get_schedule_embed(schedule[day_of_week], current_time)
        view.msg = await itr.followup.send(embed=embed, view=view)

    async def follow_autocomplete(self, _: discord.Interaction, current: str):
        choices = []
        for match in [item for item in self.anime_airing_times if item.lower().startswith(current)][:25]:
            choices.append(Choice(name=match.capitalize(), value=match))
        return choices
    
    @command(
        name='follow',
        description='Get episode alerts by following airing anime.'
    )
    @autocomplete(anime=follow_autocomplete)
    async def follow(self, itr: Interaction, anime: str):
        embed = Embed(colour=self.bot.color)

        if anime not in self.anime_airing_times:
            embed.title = f"❌ {anime} is not currently airing"
            embed.description = "Check `/anime upcoming` to see all currently airing anime."
            return await itr.response.send_message(embed=embed, ephemeral=True)

        check_query = "SELECT 1 FROM anime_users WHERE anime_title = %s AND user_id = %s"
        already_follows = await self.bot.db.fetchone(check_query, anime, itr.user.id)

        if already_follows:
            embed.title = f"🔁 You're already following **{anime}**"
            embed.description = "Do you want to unfollow?"
            buttons = ConfirmUnfollowView(self.bot, anime, itr.user.id)
            await itr.response.send_message(embed=embed, view=buttons)
            buttons.message = await itr.original_response()
            return

        try:
            dm_embed = Embed(
                title=f"✅ You're now following **{anime}**",
                description="I'll DM you whenever a new episode airs!",
                colour=discord.Color.green()
            )
            await itr.user.send(embed=dm_embed)

        except discord.Forbidden:
            embed.title = "🚫 Could not send DM"
            embed.description = (
                "Your DMs are closed! I can't send anime notifications.\n"
                "Please enable DMs and try again. <:Sadge:885924438745423893>"
            )
            return await itr.response.send_message(embed=embed, ephemeral=True)

        insert_query = "INSERT INTO anime_users (anime_title, user_id) VALUES (%s, %s)"
        await self.bot.db.execute(insert_query, anime, itr.user.id)

        embed.title = f"📩 Followed **{anime}**"
        embed.description = "You’ll receive notifications in your DM when the episode releases!"
        await itr.response.send_message(embed=embed, ephemeral=True)

        data = self.anime_airing_times[anime]
        air_datetime = get_air_time(data['day'], data['time'])

        if job_exists(self.bot, anime):
            return
        
        self.bot.scheduler.add_job(
            anime_reminder,
            trigger="date",
            run_date=air_datetime,
            args=[self.bot, anime, self.anime_airing_times],
            id=anime.replace(" ", "_")
        )

    @command(
        name='random',
        description='Get a random anime recommendation to watch.'
    )
    @describe(
        type="Choose the type of anime (tv, movie, ova, etc)",
        status="Filter by status (airing, complete, upcoming)"
    )
    async def random(
        self, itr: Interaction, 
        status: Literal['complete', 'airing', 'upcoming']='complete', 
        type: Literal['tv', 'special', 'movie'] = 'tv'
    ):
        await itr.response.defer()
        page = random.randint(1, 10)
        random_anime = random.randint(0, 24)
        api = f"https://api.jikan.moe/v4/anime?type={type}&status={status}&min_score=7&order_by=score&sort=desc&limit=25&page={page}"

        resp = requests.get(api)
        if resp.status_code != 200:
            return await itr.followup.send('API server seems to be down, try again later.',ephemeral=True)
        
        anime = resp.json()['data'][random_anime]
        embed = discord.Embed(
                title=anime['title_english'],
                url=anime['url'],
                description=anime.get('synopsis', 'No synopsis available').replace('[Written by MAL Rewrite]', '').strip(),
                colour=0x7F00FF
            )

        embed.set_image(url=anime.get('images', {}).get('jpg', {}).get('large_image_url'))
        embed.add_field(name="Type", value=anime.get('type', 'N/A'), inline=True)
        embed.add_field(name="Status", value=anime.get('status', 'N/A'), inline=True)
        embed.add_field(name="Score", value=f"{anime.get('score', 'N/A')} ({anime.get('scored_by', 0):,} votes)", inline=True)

        embed.add_field(name="Episodes", value=anime.get('episodes', 'N/A'), inline=True)
        embed.add_field(name="Duration", value=anime.get('duration', 'N/A'), inline=True)
        embed.add_field(name="Rank", value=f"#{anime.get('rank', 'N/A')}", inline=True)

        embed.add_field(name="Season", value=anime.get('season', 'N/A').title() if anime.get('season') else "N/A", inline=True)
        embed.add_field(name="Year", value=str(anime.get('year', 'N/A')), inline=True)

        studios = ", ".join([studio["name"] for studio in anime.get("studios", [])]) or "N/A"
        embed.add_field(name="Studios", value=studios, inline=True)

        return await itr.followup.send(embed=embed)
    

async def setup(bot):
    await bot.add_cog(Anime(bot))