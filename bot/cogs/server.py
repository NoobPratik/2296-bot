from collections import defaultdict
import io
import os
import logging
from time import time
import traceback
from typing import TYPE_CHECKING, Any, Dict, Optional

from aiohttp import web
import discord
from discord.ext import commands
from bot.utils.types import CodeMessage

FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID"))

if TYPE_CHECKING:
    from bot.bot import MyBot

class LeetCodeService:
    def __init__(self, bot):
        self.bot = bot
        self.language_prefix = {
            'C++': '.cpp', 'Java': '.java', 'Python': '.py', 'Python3': '.py',
            'JavaScript': '.js', 'TypeScript': '.ts', 'C': '.c',
            'C#': '.cs', 'Go': '.go', 'Rust': '.rs'
        }

    async def find_forum_thread(self, forum_id: str, title: str):
        forum = await self.bot.fetch_channel(int(forum_id))
        if not isinstance(forum, discord.ForumChannel):
            return None, None

        target_title = title.strip().lower()
        for thread in forum.threads:
            if thread.name.strip().lower() == target_title:
                return forum, thread

        async for thread in forum.archived_threads():
            if thread.name.strip().lower() == target_title:
                return forum, thread

        return forum, None

    async def send_embed(self, data: CodeMessage, thread: Optional[discord.Thread], forum: discord.ForumChannel):
        ext = self.language_prefix.get(data.language, '.txt').lstrip('.')
        filename = f"{data.url_slug}.{ext}"

        file = discord.File(io.StringIO(data.code), filename=filename)
        url = f"https://leetcode.com/problems/{data.url_slug}"
        difficulty = data.difficulty.capitalize()
        language = data.language.capitalize()

        embed = discord.Embed(
            title=data.title,
            url=url,
            description=f"**Difficulty**: {difficulty}\n**Language**: {language}\n**Time Taken**: {data.time_taken}",
            color=discord.Color.green() if difficulty == "Easy" else
                  discord.Color.orange() if difficulty == "Medium" else
                  discord.Color.red()
        )
        embed.set_author(name=f"Code by {data.user}")
        embed.set_footer(text="LeetCode submission")

        if not thread:
            thread = await forum.create_thread(
                name=data.title,
                embed=embed,
                files=[file]
            )
        else:
            await thread.send(embed=embed, file=file)

        return {"status": "success", "status_code": 200}     

class ActiveUsers:
    def __init__(self):
        self.users = defaultdict(dict)

    def user_login(self, username: str) -> None:
        self.users[username] = {
            "status": "idle",
            "question": None,
            "started_at": None,
            "solved_today": 0,
        }

    def user_logout(self, username: str) -> None:
        self.users.pop(username, None)

    def update_activity(self, username: str, status: str, question: Optional[str]) -> None:
        user = self.users.setdefault(username, {
            "status": "idle",
            "question": None,
            "started_at": None,
            "solved_today": 0,
        })
        user["status"] = status
        user["question"] = question if status == "solving" else None
        user["started_at"] = time() if status == "solving" else None

    def increment_solved(self, username: str) -> None:
        user = self.users.setdefault(username, {
            "status": "idle",
            "question": None,
            "started_at": None,
            "solved_today": 0,
            "last_active": time()
        })
        user["solved_today"] += 1

    def get_users(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.users)

API_KEY = os.getenv("API_KEY")
@web.middleware
async def api_key_middleware(request, handler):
    if request.path.startswith("/api/leetcode") and request.headers.get("X-API-KEY") != API_KEY:
        return web.json_response({"error": "Invalid API Key"}, status=403)
    return await handler(request)

class SocketServerCog(commands.Cog):
    def __init__(self, bot: 'MyBot', ip:str = '0.0.0.0', port:int = 8001):
        self.bot = bot
        self.logger = logging.getLogger("SocketServer")
        self.app = web.Application(middlewares=[api_key_middleware])
        self.runner = web.AppRunner(self.app)

        self.leetcode = LeetCodeService(bot)
        self.user_manager = ActiveUsers()

        self.ip = ip
        self.port = port

        self.setup_routes()
        self.bot.loop.create_task(self.run_server())

    def setup_routes(self):
        self.app.router.add_post("/api/leetcode/submit", self.submit)
        self.app.router.add_post("/api/leetcode/open", self.user_login)
        self.app.router.add_post("/api/leetcode/close", self.user_logout)
        self.app.router.add_post("/api/leetcode/activity", self.user_activity)
        self.app.router.add_get("/api/leetcode/online", self.get_online_users)

    async def run_server(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, host=self.ip, port=self.port)
        await site.start()
        self.logger.info(f"Socket server running on {self.ip}:{self.port}")

    async def cog_unload(self):
        await self.runner.cleanup()
        self.logger.info("Socket server shut down.")

    async def submit(self, request: web.Request):
        try:
            json_data = await request.json()
            data = CodeMessage(**json_data)

            if data.type != "DISCORD_FORUM":
                return web.json_response({"error": "Unsupported type"}, status=400)

            self.user_manager.increment_solved(data.user)

            forum, thread = await self.leetcode.find_forum_thread(data.forum_id, data.title)
            if not forum:
                return web.json_response({"error": "Forum not found"}, status=404)

            resp = await self.leetcode.send_embed(data, thread, forum)
            return web.json_response(resp, status=resp['status_code'])

        except Exception as e:
            self.logger.error(f"Error in /submit: {e}")
            self.logger.debug(traceback.format_exc())
            return web.json_response({"error": str(e)}, status=500)

    async def user_login(self, request: web.Request):
        data = await request.json()
        username = data.get("username")
        if not username:
            return web.json_response({"error": "Missing username"}, status=422)

        self.user_manager.user_login(username)
        return web.json_response({"status": "ok"})

    async def user_logout(self, request: web.Request):
        data = await request.json()
        username = data.get("username")
        if not username:
            return web.json_response({"error": "Missing username"}, status=422)

        self.user_manager.user_logout(username)
        return web.json_response({"status": "ok"})

    async def user_activity(self, request: web.Request):
        data = await request.json()
        username = data.get("username")
        if not username:
            return web.json_response({"error": "Missing username"}, status=422)

        status = data.get("status", "idle")
        question = data.get("question", None)
        self.user_manager.update_activity(username, status, question)
        return web.json_response({"status": "ok"})

    async def get_online_users(self, request: web.Request):
        return web.json_response(self.user_manager.get_users())
        

async def setup(bot):
    ip = '::' if bot.is_docker else '0.0.0.0'
    await bot.add_cog(SocketServerCog(bot, ip=ip))