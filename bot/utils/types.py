from dataclasses import dataclass
from typing import TypedDict

import aiomysql


@dataclass
class Crosshair:
    label: str
    code: str
    image_bytes: bytes

class CodeMessage(TypedDict):
    type: str
    title: str
    user: str
    runtime: str
    memory: str
    code: str
    time_taken: str
    url_slug: str
    forum_id: int
    language: str

class AttrDict(dict):

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return None


class AttrDictCursor(aiomysql.DictCursor):
    dict_type = AttrDict