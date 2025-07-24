import logging
from typing import List, Optional
import dotenv
import aiomysql
import os

from bot.utils.types import AttrDict, AttrDictCursor

dotenv.load_dotenv()
log = logging.getLogger(__name__)


class Database(object):
    """ Main class for database connection """

    def __init__(self, dev):
        self.music = None
        self.dev = dev

    async def db_get_pools(self) -> None:
        try:
            self.music = await self.mysql_create_pool()
            log.info("[Database] MySQL connection pools created!")
        except Exception as e:
            self.music = None
            log.warning(f"[Database] Could not connect to MySQL: {e}")

    async def db_close(self) -> None:
        if self.music:
            self.music.close()
            await self.music.wait_closed()

        log.info("[Database] MySQL connection pools closed! ")

    async def mysql_create_pool(self) -> aiomysql.Pool:

        is_docker = os.getenv("IS_DOCKER", False)

        host = os.getenv("MYSQL_HOST", "localhost") if not is_docker else "mysql"
        user = os.getenv("MYSQL_USER", "root")
        password = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD"))
        db = os.getenv("MYSQL_DATABASE", "main") if not self.dev else "dev"
        port = int(os.getenv("MYSQL_PORT", 3306))

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
            conn: aiomysql.Connection
            async with conn.cursor(AttrDictCursor) as cur:
                cur: aiomysql.Cursor
                await cur.execute(sql, args)
                return await cur.fetchone()

    async def fetchall(self, sql, *args) -> List[AttrDict]:
        async with self.music.acquire() as conn:
            conn: aiomysql.Connection
            async with conn.cursor(AttrDictCursor) as cur:
                cur: aiomysql.Cursor
                await cur.execute(sql, args)
                return await cur.fetchall()

