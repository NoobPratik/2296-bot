import asyncio
import contextlib
import logging
from logging.handlers import RotatingFileHandler
import os
import click
from bot.bot import MyBot

from dotenv import load_dotenv
load_dotenv()


@contextlib.contextmanager
def setup_logging():
    log = logging.getLogger()

    class RemoveNoise(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return not (record.levelname == 'WARNING' and 'referencing an unknown' in record.msg)

    class SuppressGatewaySpam(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            msg = record.getMessage()
            return not any(kw in msg for kw in ('Shard ID', 'WebSocket closed'))

    try:
        max_bytes = 8 * 1024 * 1024  # 8 MiB
        log.setLevel(logging.INFO)

        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')

        os.makedirs('logs', exist_ok=True)
        file_handler = RotatingFileHandler(
            filename='./logs/2296-bot.log', encoding='utf-8', mode='w', maxBytes=max_bytes, backupCount=3
        )
        file_handler.setFormatter(fmt)
        log.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(fmt)
        log.addHandler(console_handler)

        logging.getLogger('discord').setLevel(logging.WARNING)
        logging.getLogger('discord.gateway').setLevel(logging.ERROR)
        logging.getLogger('discord.gateway').addFilter(SuppressGatewaySpam())
        logging.getLogger('discord.client').setLevel(logging.ERROR)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('discord.state').addFilter(RemoveNoise())

        logging.getLogger('apscheduler').setLevel(logging.WARNING)
        yield

    finally:
        for h in log.handlers[:]:
            h.close()
            log.removeHandler(h)


async def run_bot(dev):
    bot = MyBot(dev=dev)
    token = os.environ['DISCORD_DEV'] if dev else os.environ['DISCORD_MAIN']

    try:
        await bot.start(token, reconnect=True)
    except (KeyboardInterrupt, RuntimeError):
        pass

@click.command()
@click.option('--dev', is_flag=True, help='Enable developer bot mode.')
def main(dev):
    with setup_logging():
        asyncio.run(run_bot(dev))


if __name__ == '__main__':
    main()
