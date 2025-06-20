import logging
from typing import List, Optional
import dotenv
import aiomysql
import os

dotenv.load_dotenv()
log = logging.getLogger(__name__)


class AttrDict(dict):

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return None


class AttrDictCursor(aiomysql.DictCursor):
    dict_type = AttrDict


class Database(object):
    """ Main class for database connection """

    def __init__(self):
        self.music = None

    async def db_get_pools(self):
        self.music = await self.mysql_create_pool()
        log.info("[Database] MySQL connection pools created!")

    async def db_close(self):
        if self.music:
            self.music.close()
            await self.music.wait_closed()

        log.info("[Database] MySQL connection pools closed! ")

    @staticmethod
    async def mysql_create_pool():
        host = os.getenv("MYSQL_HOST", "localhost")
        user = os.getenv("MYSQL_USER")
        password = os.getenv("MYSQL_PASSWORD")
        db = os.getenv("MYSQL_DATABASE", "db")
        port = int(os.getenv("MYSQL_PORT"))

        return await aiomysql.create_pool(
            host=host,
            user=user, password=password,
            db=db, port=port, autocommit=True
        )

    async def execute(self, sql, *args) -> None:
        async with self.music.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                await conn.commit()

    async def fetchone(self, sql, *args) -> Optional[AttrDict]:
        async with self.music.acquire() as conn:
            async with conn.cursor(AttrDictCursor) as cur:
                await cur.execute(sql, args)
                return await cur.fetchone()

    async def fetchall(self, sql, *args) -> List[AttrDict]:
        async with self.music.acquire() as conn:
            async with conn.cursor(AttrDictCursor) as cur:
                await cur.execute(sql, args)
                return await cur.fetchall()

