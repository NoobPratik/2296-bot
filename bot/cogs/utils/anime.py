from collections import defaultdict
import datetime as dt
import aiohttp
import discord
import pytz
import requests

async def jikan_search_anime(query: str, limit: int = 10):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.jikan.moe/v4/anime?q={query}&limit={limit}") as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("data", [])

async def jikan_top_anime(limit: int = 25, page: int = 1, filter: str = None, type: str = None):
    base_url = f"https://api.jikan.moe/v4/top/anime?limit={limit}&page={page}"
    if filter:
        base_url += f"&filter={filter}"
    if type:
        base_url += f"&type={type}"

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("data", [])
        
async def fetch_top_anime_page(page: int, filter: str = None, type: str = None):
    results = await jikan_top_anime(limit=25, page=page, filter=filter, type=type)
    if not results:
        return []

    chunk_size = 5
    pages = []

    for i in range(0, len(results), chunk_size):
        chunk = results[i:i + chunk_size]
        start_rank = chunk[0].get("rank", "?")
        end_rank = chunk[-1].get("rank", "?")

        embed = discord.Embed(
            title=f"Top Anime (Rank {start_rank} - {end_rank})",
            colour=0x7F00FF
        )

        for anime in chunk:
            title = anime["title"]
            url = anime["url"]
            score = anime.get("score", "N/A")
            rank = anime.get("rank", "N/A")
            episodes = anime.get("episodes", "N/A")

            embed.add_field(
                name=f"#{rank}: {title}",
                value=f"**Score:** {score} | **Episodes:** {episodes} | [Link]({url})",
                inline=False
            )

        pages.append(embed)
    return pages

def get_schedule_embed(animes, current_time: dt.datetime) -> discord.Embed:
    embed = discord.Embed(title="📺 Upcoming Anime Schedule", colour=0x7F00FF)
    desc = [
        f"**[{anime['title']}](https://animekai.bz/browser?keyword={anime['title'].replace(' ', '+')})**: {anime['time']}"
        for anime in animes
    ]
    embed.description = "\n".join(desc) if desc else "No anime scheduled for today."
    formatted_time = current_time.strftime("%a • %I:%M %p IST")
    embed.set_footer(text=f"🕒 {formatted_time}")
    return embed

async def anime_reminder(bot, anime, anime_airing_times):
    anime_records = await bot.db.fetchall("SELECT * FROM anime_users WHERE anime_title = %s", anime)
    if not anime_records:
        return

    embed = discord.Embed(colour=bot.color)
    embed.set_image(url=f'https://subsplease.org/{anime_airing_times[anime]["image_url"]}')
    embed.set_footer(icon_url=bot.user.avatar.url,text=bot.user.name)

    for record in anime_records:
        user: discord.User = bot.get_user(record['user_id'])
        embed.title = f'Hey, {user.display_name}'
        embed.description = f'New episode of [{anime}](https://subsplease.org/shows/{anime.replace(" ", "-")}) is out now! <a:3285nezukojump:1159302086845022270>'
        try:
            await user.send(embed=embed)
        except Exception as e:
            print(e)

async def anime_remainder_schedule(bot) -> dict:
    anime_airing_times = get_anime_airing()
    for anime, data in anime_airing_times.items():

        anime_record = await bot.db.fetchone('SELECT 1 FROM anime_users WHERE anime_title = %s', anime)
        if not anime_record:
            continue

        air_datetime = get_air_time(data['day'], data['time'])
        if not job_exists(bot, anime):
            bot.scheduler.add_job(
                anime_reminder,
                trigger="date",
                run_date=air_datetime,
                args=[bot, anime, anime_airing_times],
                id=anime
            )
    return anime_airing_times

def get_anime_airing():
    r = requests.get('https://subsplease.org/api/?f=schedule&tz=Asia/Calcutta')
    anime_data = r.json()['schedule']
    anime_airing_times = defaultdict()

    for day, anime_list in anime_data.items():

        for anime in anime_list:
            title = anime['title'].lower()
            time = anime['time']
            anime_airing_times[title] = {'day': day, 'time': time, 'image_url': anime['image_url']}

    return anime_airing_times

def get_air_time(day: str, time_str: str) -> dt.datetime:
    tz = pytz.timezone("Asia/Calcutta")
    now = dt.datetime.now(tz)

    hour, minute = map(int, time_str.split(":"))
    target_time = dt.time(hour, minute)

    weekday_index = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day)
    days_ahead = (weekday_index - now.weekday()) % 7

    # If today but time has already passed, schedule for next week
    if days_ahead == 0 and now.time() > target_time:
        days_ahead = 7

    target_date = now + dt.timedelta(days=days_ahead)
    return tz.localize(dt.datetime.combine(target_date.date(), target_time))

def job_exists(bot, anime) -> bool:
    if bot.scheduler.get_job(anime):
        return True
    return False

# def convert_jst_to_ist(day: str, time_str: str) -> tuple[str, str]:
#     """Convert day and time from JST to IST."""
#     if not time_str:
#         return day, "00:00"

#     jst = pytz.timezone("Asia/Tokyo")
#     ist = pytz.timezone("Asia/Calcutta")

#     hour, minute = map(int, time_str.split(":"))

#     now = dt.datetime.now()
#     weekday = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day.capitalize())
#     base_date = now + dt.timedelta(days=(weekday - now.weekday()) % 7)
#     jst_time = jst.localize(dt.datetime.combine(base_date.date(), dt.time(hour, minute)))

#     ist_time = jst_time.astimezone(ist)

#     ist_day = ist_time.strftime("%A")
#     ist_time_str = ist_time.strftime("%H:%M")
#     return ist_day, ist_time_str

# async def get_anime_airing():
#     anime_airing_times = defaultdict(dict)
#     async with aiohttp.ClientSession() as session:
#         for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
#             async with session.get(f"https://api.jikan.moe/v4/schedules?filter={day}") as resp:
#                 if resp.status != 200:
#                     continue
#                 data = (await resp.json()).get("data", [])

#                 for anime in data:
#                     title = anime.get("title_english") or anime["title"]
#                     jst_time = anime.get("broadcast", {}).get("time")
#                     image_url = anime.get("images", {}).get("jpg", {}).get("image_url")

#                     if not jst_time:
#                         continue

#                     ist_day, ist_time = convert_jst_to_ist(day, jst_time)

#                     anime_airing_times[title.lower()] = {
#                         "day": ist_day,
#                         "time": ist_time,
#                         "image_url": image_url,
#                         "mal_id": anime["mal_id"]
#                     }
#     return anime_airing_times
