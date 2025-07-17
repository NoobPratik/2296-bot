import os
import logging
from typing import TYPE_CHECKING, Optional

from aiohttp import web
import discord
from discord.ext import commands
from bot.utils.types import CodeMessage

FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID"))

if TYPE_CHECKING:
    from bot.bot import MyBot

class LeetCode:
    def __init__(self, bot: 'MyBot', data: CodeMessage):
        self.bot = bot
        self.data = data
        self.language_prefix = {'python': 'py'}

    async def find_forum_thread(self):
        forum = await self.bot.fetch_channel(self.data['forum_id'])
        if not isinstance(forum, discord.ForumChannel):
            return None, None

        target_title = self.data["title"].strip().lower()

        for thread in forum.threads:
            if thread.name.strip().lower() == target_title:
                return forum, thread

        async for thread in forum.archived_threads(limit=None):
            if thread.name.strip().lower() == target_title:
                return forum, thread

        return forum, None
    
    async def send_leetcode_embed(self, data: CodeMessage, thread: Optional[int], forum: discord.channel.ForumChannel):

        if not thread and forum:
            return {'status': 'error', 'status_code': 400, 'error': 'provided forum id is invalid'}

        if not thread:
            thread = await forum.create_thread(name=data["title"], content=content, embed=embed)

        embed = discord.Embed(
            title=f"Code by {data.get('user', 'unknown')}",
            description=f"```{self.language_prefix[data.get('language')]}\n{data.get('code', '')}```",
            color=self.bot.color
        )
        embed.set_footer(text=f"Runtime: {data.get('runtime')}, Memory: {data.get('memory')}, Time taken: {data.get('time_taken')}")
        content = f"<https://leetcode.com/problems/{data.get('url_slug', 'unknown')}>"

        try:
            await thread.send(content=content, embed=embed)
            return {'status': 'success', 'status_code': 200}
        
        except Exception as e:
            return {'status': 'error', 'status_code': 400, 'error': e}
        

class SocketServerCog(commands.Cog):
    def __init__(self, bot: 'MyBot', ip:str = '0.0.0.0', port:int = 6969):
        self.bot = bot
        self.logger = logging.getLogger("SocketServer")
        self.app = web.Application()
        self.runner = web.AppRunner(self.app)
        self.ip = ip
        self.port = port

        self.setup_routes()
        self.bot.loop.create_task(self.run_server())

    def setup_routes(self):
        self.app.router.add_post("/api/leetcode", self.route_submit)

    async def run_server(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, host=self.ip, port=self.port)
        await site.start()
        self.logger.info(f"Socket server is running on port {self.ip}:{self.port}")

    async def route_submit(self, request: web.Request):
        if request.headers.get("X-API-KEY") != os.getenv("API_KEY"):
            return web.json_response({"error": "Unauthorized"}, status=403)

        try:
            data: CodeMessage = await request.json()

            if data.get("type") != "DISCORD_FORUM":
                return web.json_response({"error": "Unsupported type"}, status=400)
            
            leetcode = LeetCode(self.bot, data)

            forum, thread = await leetcode.find_forum_thread()
            resp = await leetcode.send_leetcode_embed(data, thread, forum)

            return web.json_response(resp, status=resp['status_code'])

        except Exception as e:
            self.logger.error(f"Error in /submit: {e}")
            return web.json_response({"error": str(e)}, status=500)


async def setup(bot):
    await bot.add_cog(SocketServerCog(bot))