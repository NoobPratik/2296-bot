import asyncio
import contextlib
import logging
from logging.handlers import RotatingFileHandler
import os
import click
from bot.bot import MyBot

from dotenv import load_dotenv
load_dotenv()

class RemoveNoise(logging.Filter):
    def __init__(self):
        super().__init__(name='discord.state')

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
            return False
        return True


@contextlib.contextmanager
def setup_logging():
    log = logging.getLogger()

    class RemoveNoise(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return not (record.levelname == 'WARNING' and 'referencing an unknown' in record.msg)

    class SuppressWavelinkConnectionErrors(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return 'refused the network connection' not in record.getMessage()

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

        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('discord.state').addFilter(RemoveNoise())

        logging.getLogger('wavelink.websocket').addFilter(SuppressWavelinkConnectionErrors())

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
