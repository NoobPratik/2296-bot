from urllib.parse import quote
from discord import Interaction
from typing import TYPE_CHECKING

import discord
from pomice import LoopMode, Playlist, PlaylistType, Track, TrackType

if TYPE_CHECKING:
    from bot import MyBot
    from bot.cogs.music import MusicPlayer
    from bot.utils.database import Database

def same_vc(itr: Interaction, player: 'MusicPlayer'):
    if not itr.user.voice:
        return False
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

async def reset_embeds(music, player: 'MusicPlayer'):
    """Resets the music embed and queue embed"""

    if not player or not player.guild:
        return

    guild = await music.bot.db.fetchone("SELECT * FROM music WHERE guild_id = %s", player.guild.id)

    if not guild:
        return

    await player.destroy()
    player.queue.clear()

    channel = player.guild.get_channel(guild['channel_id'])
    message = await channel.fetch_message(guild['message_id'])
    queue_message = await channel.fetch_message(guild['queue_id'])

    embed, embed2 = default_embed(music.view.bot)

    disabled_buttons(music.view.children)

    if not message.embeds or message.embeds[0].description != embed.description:
        await message.edit(embed=embed, view=music.view)

    if not queue_message.embeds or queue_message.embeds[0].description != embed2.description:
        await queue_message.edit(embed=embed2)

async def now_playing(music, player: 'MusicPlayer'):
    guild = await music.db.fetchone("SELECT * FROM music WHERE guild_id = %s", player.guild.id)
    channel = player.guild.get_channel(guild['channel_id'])
    msg = await channel.fetch_message(guild['message_id'])
    autoplay_status = "(Autoplay Enabled)" if player.autoplay else ""

    embed = discord.Embed(title=f'Currently Playing {autoplay_status}', color=music.bot.color)
    embed.description = (
        f'[{player.current.title}]({player.current.uri}) - by **{player.current.author}**'
    )
    embed.set_image(url=player.current.thumbnail)

    if player.current.requester:
        requested_by = f'Requested by {player.current.requester.display_name} - ({get_duration(player.current.length)})'
    else:
        requested_by = f'Added by Autoplay - ({get_duration(player.current.length)})'

    embed.set_footer(text=requested_by,icon_url=music.bot.user.avatar.url)
    enabled_buttons(music.view.children)

    if not msg.embeds or msg.embeds[0].description != embed.description:
        await msg.edit(embed=embed, view=music.view)

async def update_queue(bot: 'MyBot', db: 'Database', player: 'MusicPlayer') -> None:
    guild = await db.fetchone("SELECT * FROM music WHERE guild_id = %s", player.guild.id)
    channel = player.guild.get_channel(guild['channel_id'])
    queue_message = await channel.fetch_message(guild['queue_id'])

    loop_status = "(Song Loop)" if player.queue.loop_mode == LoopMode.TRACK else \
                  "(Queue Loop)" if player.queue.loop_mode == LoopMode.QUEUE else ""
    
    if player.queue.is_empty and player.autoplay and not player.queue.loop_mode:
        recommendations = await _get_recommendations(track=player.current, player=player)
        # recommendations = await player.get_recommendations(track=player.current)
        if recommendations:
            player.queue.extend(recommendations.tracks)

    desc = []
    for i, song in enumerate(list(player.queue.get_queue())[:10], start=1):
        song: Track
        desc.append(
            f"**{i}. {song.title}**"
            f'[{song.author} 'f'({get_duration(song.length)})]({song.uri})'
        )

    if player.queue.count > 10:
        desc.append(f'{player.queue.count - 10} More songs.....')

    embed = discord.Embed(
        title=f'Queue | {player.queue.count} Songs {loop_status}',
        description="\n".join(desc),
        color=bot.color
    )

    if not queue_message.embeds or queue_message.embeds[0].description != embed.description:
        await queue_message.edit(embed=embed)

async def _get_recommendations(track: Track, player: 'MusicPlayer') -> Playlist:
    uri = f"https://www.youtube.com/watch?v={track.identifier}&list=RD{track.identifier}"
    query = f"identifier={quote(uri)}"

    data = await player.node.send(
        method="GET",
        path="loadtracks",
        query=query,
    )

    tracks = [
        Track(
            track_id=track["encoded"],
            info=track["info"],
            track_type=TrackType(track["info"]["sourceName"]),
        )
        for track in data['data']['tracks'][1:]
    ]

    return Playlist(
        playlist_info=data.get('playlistInfo', {}),
        tracks=tracks,
        playlist_type=PlaylistType(tracks[0].track_type.value),
        thumbnail=tracks[0].thumbnail,
        uri=uri,
    )