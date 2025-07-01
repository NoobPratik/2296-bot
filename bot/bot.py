import logging
import os
import random
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands, tasks
from discord.ext.commands import Context
import pomice
import dotenv
from bot.utils.database import Database

dotenv.load_dotenv()
dev_guild = discord.Object(id=863032719314911262)
logger = logging.getLogger(__name__)


class MyBot(commands.Bot):
    def __init__(self, dev=False):
        self.db = Database()
        self.ready = True
        self.color = 0x7F00FF
        self.dev = dev
        self.scheduler = AsyncIOScheduler()
        self._cogs = [
            'anime',
            'admin',
            'music',
            'games',
            'valorant',
            'miscellaneous',
            'help',
            'errors'
        ]

        self.pomice = pomice.NodePool()
        self.economy_enabled = False
        super().__init__(command_prefix='!',intents=discord.Intents.all())

    async def setup_hook(self):
        logging.info("Setup Initiated.")
        for cog in self._cogs:
            await self.load_extension(f"bot.cogs.{cog}")
            logging.info(f"Loaded {cog} cog")

        self.scheduler.start()
        await self.db.db_get_pools()
        
        logging.info("Setup Complete.")

    @discord.utils.cached_property
    def webhook(self):
        wh_id = os.getenv("DISCORD_ERRORS_WEBHOOK_ID")
        wh_token = os.getenv("DISCORD_ERRORS_WEBHOOK_TOKEN")
        return discord.Webhook.partial(
            id=wh_id, token=wh_token, client=self
        )

    async def start_nodes(self):

        is_docker = os.getenv("IS_DOCKER", False)

        host = os.environ["LAVALINK_HOST"] if not is_docker else "lavalink"
        port = int(os.environ["LAVALINK_PORT"])
        password = os.environ["LAVALINK_PASSWORD"]
        identifier = os.environ.get("LAVALINK_IDENTIFIER", "MAIN")
        spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID", None)
        spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", None)

        try:
            await self.pomice.create_node(
                bot=self, host=host, 
                port=port, password=password, 
                identifier=identifier, 
                spotify_client_id=spotify_client_id, 
                spotify_client_secret=spotify_client_secret
            )
            logger.info("Lavalink node started.")
        except Exception as e:
            logger.error(f"Failed to start Lavalink node: {e}")

    async def do_sync(self):
        logging.info(
            f'Preparing for sync. [{"Development" if self.dev else "Production"}]')
        self.tree.clear_commands(guild=None)
        if not self.dev:
            return await self.tree.sync()

        self.tree.copy_global_to(guild=dev_guild)
        return await self.tree.sync(guild=dev_guild)

    async def shutdown(self):
        logging.info("Shutting down.")
        await super().close()

    async def close(self):
        logging.info("Closing...")
        await self.shutdown()

    async def on_connect(self):
        logging.info("bot connected.")

    async def on_ready(self):
        self.ready = True
        await self.start_nodes()
        logging.info("READY.")
        self.change_status.start()

    @tasks.loop(seconds=15)
    async def change_status(self):
        activity_list = [discord.Activity(type=discord.ActivityType.playing, name='Join me for some gaming fun! 🎲'),
                         discord.Activity(
                             type=discord.ActivityType.listening, name='Tunes 🎶'),
                         discord.Activity(
                             type=discord.ActivityType.watching, name='your favorite anime 📺'),
                         discord.Activity(type=discord.ActivityType.listening,
                                          name='What should I do next? You decide! 🤔'),
                         discord.Activity(type=discord.ActivityType.playing, name='/games 🎮')]
        activity = random.choice(activity_list)
        await self.change_presence(activity=activity)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is not None and ctx.guild is not None:
            if not self.ready:
                await ctx.send("I'm not ready to receive commands. Please wait a few seconds.")

            else:
                await self.invoke(ctx)

    @property
    def config(self):
        return __import__('config')
