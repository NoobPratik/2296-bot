import re
from discord import Interaction
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.cogs.music import MusicPlayer

def same_vc(itr: Interaction, player: 'MusicPlayer'):
    if itr.user.voice.channel != player.channel:
        return False
    return True

def disabled_buttons(children):
    for child in children:
        if child.custom_id in ['btn-lock', 'btn-play-liked']:
            continue
        child.disabled = True

def enabled_buttons(children):
    for child in children:
        if child.custom_id in ['disabled-1', 'disabled-2']:
            continue
        child.disabled = False

def get_duration(duration):
    seconds = duration // 1000
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    remaining_seconds = seconds % 60

    if hours > 0:
        formatted_time = f"{hours}:{minutes:02d}:{remaining_seconds:02d}"
    else:
        formatted_time = f"{minutes}:{remaining_seconds:02d}"

    return formatted_time

def default_embed(bot):
    embed = discord.Embed(title='Currently Playing Nothing.', color=bot.color)
    embed.set_image(
        url='https://media.discordapp.net/attachments/885924272781000746/1157565953631068171/image.png')
    embed.set_footer(text=f'2296 - Music', icon_url=bot.user.avatar.url)
    embed.description = ''
    embed2 = discord.Embed(title='Current Queue |', color=bot.color)
    return embed, embed2

def is_youtube_or_spotify_link(text):
    if re.match(r"(?i)(https?://(?:www\.)?youtu(?:be\.com|\.be)/(?:watch\?v=)?([\w-]{11}))", text):
        return True
    if re.match(r"(https://open\.spotify\.com/(?:\w+/)?(\w+)/(\w+))", text):
        return True
    return False

