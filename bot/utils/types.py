from dataclasses import dataclass

import aiomysql


@dataclass
class Crosshair:
    label: str
    code: str
    file_bytes: bytes

class AttrDict(dict):

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return None


class AttrDictCursor(aiomysql.DictCursor):
    dict_type = AttrDict