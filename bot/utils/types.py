from dataclasses import dataclass
from typing import Optional, TypedDict

import aiomysql
from pydantic import BaseModel


@dataclass
class Crosshair:
    label: str
    code: str
    image_bytes: bytes

class CodeMessage(BaseModel):
    title: str
    code: str
    language: str
    url_slug: str
    forum_id: str
    difficulty: Optional[str] = "Unknown"
    time_taken: Optional[str] = "N/A"
    user: Optional[str] = "Anonymous"
    type: Optional[str] = "DISCORD_FORUM"
    
class AttrDict(dict):

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return None


class AttrDictCursor(aiomysql.DictCursor):
    dict_type = AttrDict