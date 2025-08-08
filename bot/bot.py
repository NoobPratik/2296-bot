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

ACTIVITY_LIST = [
    discord.Activity(type=discord.ActivityType.playing, name='Join me for some gaming fun! 🎲'),
    discord.Activity(type=discord.ActivityType.listening, name='Tunes 🎶'),
    discord.Activity(type=discord.ActivityType.watching, name='your favorite anime 📺'),
    discord.Activity(type=discord.ActivityType.listening,name='What should I do next? You decide! 🤔'),
    discord.Activity(type=discord.ActivityType.playing, name='/games 🎮')
]

COGS = [
    'anime',
    'music',
    'games',
    'valorant',
    'miscellaneous',
    'help',
    'errors',
    'admin',
    'server'
]


class MyBot(commands.Bot):
    def __init__(self, dev=False):
        self.db = Database(dev)
        self.color = 0x7F00FF
        self.dev = dev

        self.scheduler = AsyncIOScheduler()
        self.pomice = pomice.NodePool()

        self.economy_enabled = False
        self.is_docker = os.getenv("IS_DOCKER", False)
        prefix = '.' if dev else '!'
        super().__init__(command_prefix=prefix, intents=discord.Intents.all())

    async def setup_hook(self):
        logging.info("Setup Initiated.")
        for cog in COGS:
            await self.load_extension(f"bot.cogs.{cog}")
            logging.info(f"Loaded {cog} cog")

        self.scheduler.start()
        await self.db.db_get_pools()
        
        if self.is_docker:
            await self.do_sync()
            
        logging.info("Setup Complete.")

    @discord.utils.cached_property
    def webhook(self):
        wh_id = os.getenv("DISCORD_ERRORS_WEBHOOK_ID")
        wh_token = os.getenv("DISCORD_ERRORS_WEBHOOK_TOKEN")
        return discord.Webhook.partial(
            id=wh_id, token=wh_token, client=self
        )

    async def start_nodes(self):

        host = os.environ["LAVALINK_HOST"] if not self.is_docker else "lavalink"
        port = int(os.environ["LAVALINK_PORT"])
        password = os.environ["LAVALINK_PASSWORD"]
        identifier = os.environ.get("LAVALINK_IDENTIFIER", "MAIN")

        try:
            await self.pomice.create_node(
                bot=self, 
                host=host, 
                port=port, 
                password=password, 
                identifier=identifier,
            )
            logging.info("Lavalink node started successfully.")
            return True
        except Exception as e:
            logging.error(f"Failed to start Lavalink node: {e}")
            return False

    async def do_sync(self) -> None:
        mode = "Development" if self.dev else "Production"
        logging.info(f"Preparing for sync. [{mode}]")

        if not self.dev:
            return await self.tree.sync()

        dev_guild_id = int(os.getenv("DEV_GUILD_ID", 863032719314911262))
        dev_guild = discord.Object(id=dev_guild_id)
        self.tree.clear_commands(guild=dev_guild)
        return await self.tree.sync(guild=dev_guild)

    async def shutdown(self) -> None:
        logging.info("Shutting down.")
        try:
            self.scheduler.shutdown(wait=False)
            await self.pomice.cleanup()
            await self.db.close()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        await super().close()

    async def close(self):
        logging.info("Closing...")
        await self.shutdown()

    async def on_connect(self):
        logging.info("bot connected.")

    async def on_ready(self):
        await self.start_nodes()
        logging.info("READY.")
        self.change_status.start()

    @tasks.loop(seconds=15)
    async def change_status(self):

        activity = random.choice(ACTIVITY_LIST)
        await self.change_presence(activity=activity)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is not None and ctx.guild is not None:
            await self.invoke(ctx)

    @property
    def config(self):
        return __import__('config')
