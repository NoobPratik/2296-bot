import os
import logging
from typing import TypedDict, Optional

from aiohttp import web
import discord
from discord.ext import commands

FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID"))

class CodeMessage(TypedDict):
    type: str
    title: str
    user: str
    runtime: str
    memory: str
    code: str
    time_taken: str
    url_slug: str

class SocketServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("SocketServer")
        self.app = web.Application()
        self.runner = web.AppRunner(self.app)

        self.setup_routes()
        self.bot.loop.create_task(self.run_server())

    def setup_routes(self):
        self.app.router.add_post("/submit", self.route_submit)

    async def run_server(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, host="0.0.0.0", port=6969)
        await site.start()
        self.logger.info("Socket server is running on port 80")

    async def route_submit(self, request: web.Request):
        if request.headers.get("X-API-KEY") != os.getenv("API_KEY"):
            return web.json_response({"error": "Unauthorized"}, status=403)

        try:
            data: CodeMessage = await request.json()
            if data.get("type") != "DISCORD_FORUM":
                return web.json_response({"error": "Unsupported type"}, status=400)

            thread_id = await self.find_forum_thread(data["title"])
            await self.send_leetcode_embed(data, thread_id)

            return web.json_response({"status": "Webhook sent"}, status=200)

        except Exception as e:
            self.logger.error(f"Error in /submit: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def find_forum_thread(self, title: str) -> Optional[int]:
        forum = self.bot.get_channel(FORUM_CHANNEL_ID)
        if not isinstance(forum, discord.ForumChannel):
            return None

        for thread in forum.threads:
            if thread.name.strip().lower() == title.strip().lower():
                return thread.id
        return None

    async def send_leetcode_embed(self, data: CodeMessage, thread_id: Optional[int]):
        forum_channel = self.bot.get_channel(FORUM_CHANNEL_ID)

        if not isinstance(forum_channel, discord.ForumChannel):
            self.logger.error("Forum channel not found or invalid.")
            return

        embed = discord.Embed(
            title=f"Code by {data.get('user', 'unknown')}",
            description=f"```py\n{data.get('code', '')}```",
            color=0x00ff99
        )
        embed.set_footer(text=f"Runtime: {data.get('runtime')}, Memory: {data.get('memory')}, Time taken: {data.get('time_taken')}")
        content = f"<https://leetcode.com/problems/{data.get('url_slug', 'unknown')}>"

        if thread_id:
            thread = forum_channel.get_thread(thread_id)
            if thread is None:
                self.logger.warning(f"Thread ID {thread_id} not found, creating a new one.")
                thread = await forum_channel.create_thread(name=data["title"], content=content, embed=embed)
            else:
                await thread.send(content=content, embed=embed)
        else:
            thread = await forum_channel.create_thread(name=data["title"], content=content, embed=embed)

async def setup(bot):
    await bot.add_cog(SocketServerCog(bot))