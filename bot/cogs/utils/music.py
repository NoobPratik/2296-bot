import json
import os
from urllib.parse import quote
from discord import Interaction
from typing import TYPE_CHECKING

import discord
from pomice import LoopMode, Player, Playlist, PlaylistType, Queue, Track, TrackType
import pomice
from pomice.spotify.client import Client

if TYPE_CHECKING:
    from bot.cogs.music import MusicPlayer
    from bot.utils.database import Database

class MusicPlayer(Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.autoplay = False
        self.queue = Queue()
        self.color = 0x7F00FF
        self.last_lyrics = {}

    async def _get_lyrics(self, skip_source: bool = True) -> dict | None:
        if self.current.track_id in self.last_lyrics:
            return self.last_lyrics[self.current.track_id]
        
        path = f"sessions/{self.node._session_id}/players/{self.guild.id}/track/lyrics"
        query = f"skipTrackSource={str(skip_source).lower()}"

        try:
            response = await self.node.send(
                method="GET",
                path=path,
                query=query,
            )
        except pomice.exceptions.NodeRestException as e:
            print(e)
            return None

        if not response:
            return None

        self.last_lyrics[self.current.track_id] = response['lines']
        return response['lines']
            
    async def _get_recommendations(self) -> Playlist | None:
        if self.current.track_type == TrackType.SPOTIFY:
            return await self._get_spotify_recommendations()
        else:
            return await self._get_youtube_recommendations()

    async def _get_spotify_recommendations(self) -> Playlist | None:
        request_url = 'http://spotify-tokener:8080/api/token'
        resp = await self.node._session.get(request_url)
        data: dict = await resp.json(loads=json.loads)
        
        self._bearer_headers = {
            "Authorization": f"Bearer {data['accessToken']}",
        }
        request_url = f"https://api.spotify.com/v1/recommendations/?seed_tracks={self.current.identifier}"
        resp = await self.node._session.get(request_url, headers=self._bearer_headers)

        if resp.status != 200:
            return None

        data: dict = await resp.json(loads=json.loads)
        tracks = [Track(track) for track in data["tracks"]]

        return tracks

    async def _get_youtube_recommendations(self) -> Playlist:
        identifier = self.current.identifier
        uri = f"https://www.youtube.com/watch?v={identifier}&list=RD{identifier}"
        query = f"identifier={quote(uri)}"

        data = await self.node.send(
            method="GET",
            path="loadtracks",
            query=query,
        )

        track_data = data['data']['tracks'][1:]
        tracks = [
            Track(
                track_id=track["encoded"],
                info=track["info"],
                track_type=TrackType(track["info"]["sourceName"]),
            )
            for track in track_data
        ]

        return Playlist(
            playlist_info=data.get('playlistInfo', {}),
            tracks=tracks,
            playlist_type=PlaylistType(tracks[0].track_type.value),
            thumbnail=tracks[0].thumbnail,
            uri=uri,
        )

    def _get_embed(self, track: Track = None) -> tuple[discord.Embed, discord.Embed]:
        if not track:
            embed = discord.Embed(title='Currently Playing Nothing.', color=self.color)
            embed.set_image(url='https://media.discordapp.net/attachments/885924272781000746/1157565953631068171/image.png')
            embed.set_footer(text='2296 - Music', icon_url=self.bot.user.avatar.url)
            embed.description = ''
            queue_embed = discord.Embed(title='Current Queue |', color=self.color)
            return embed, queue_embed

        track = self.current
        autoplay_status = " (Autoplay Enabled)" if self.autoplay else ""

        embed = discord.Embed(
            title=f'Currently Playing{autoplay_status}',
            description=f'[{track.title}]({track.uri}) - by **{track.author}**',
            color=self.color
        )

        image = track.thumbnail or track.info.get('artworkUrl')
        embed.set_image(url=image)

        footer = (
            f'Requested by {track.requester.display_name} - ({get_duration(track.length)})'
            if track.requester else
            f'Added by Autoplay - ({get_duration(track.length)})'
        )
        embed.set_footer(text=footer, icon_url=self.bot.user.avatar.url)
        return embed, None

    async def now_playing(self, db: 'Database', view) -> None:
        guild = await db.fetchone("SELECT * FROM music WHERE guild_id = %s", self.guild.id)
        channel = self.guild.get_channel(guild['channel_id'])
        msg = await get_message(channel, guild['message_id'], db)
        # msg = await channel.fetch_message(guild['message_id'])

        embed, _ = self._get_embed(self.current)
        enabled_buttons(view.children)

        if not msg.embeds or msg.embeds[0].description != embed.description:
            await msg.edit(embed=embed, view=view)
    
    async def update_queue(self, db: 'Database') -> None:
        guild_config = await db.fetchone("SELECT * FROM music WHERE guild_id = %s", self.guild.id)
        if not guild_config:
            return

        channel = self.guild.get_channel(guild_config['channel_id'])
        if not channel:
            return

        try:
            queue_msg = await get_message(channel, guild_config['queue_id'], db)
            # queue_msg = await channel.fetch_message(guild_config['queue_id'])
        except discord.NotFound:
            return

        if self.queue.is_empty and self.autoplay and not self.queue.loop_mode:
            recommendations = await self._get_recommendations()
            if recommendations:
                self.queue.extend(recommendations.tracks)
                self.queue.shuffle()

        desc = []
        for i, track in enumerate(list(self.queue.get_queue())[:10], start=1):
            desc.append(
                f"**{i}. {track.title}** "
                f"[{track.author} ({get_duration(track.length)})]({track.uri})"
            )

        if self.queue.count > 10:
            desc.append(f"...and {self.queue.count - 10} more songs.")

        loop_status = (
            "(Song Loop)" if self.queue.loop_mode == LoopMode.TRACK else
            "(Queue Loop)" if self.queue.loop_mode == LoopMode.QUEUE else
            ""
        )

        embed = discord.Embed(
            title=f'Queue | {self.queue.count} Songs {loop_status}',
            description="\n".join(desc) or "The queue is currently empty.",
            color=self.color
        )

        if not queue_msg.embeds or queue_msg.embeds[0].description != embed.description:
            await queue_msg.edit(embed=embed)

async def get_message(channel: discord.TextChannel, message_id: int, db: 'Database'):
    try:
        msg = await channel.fetch_message(message_id)
        return msg
    except discord.NotFound:
        await db.execute(
            "DELETE FROM music WHERE channel_id = %s AND guild_id = %s",
            channel.id, channel.guild.id
        )
        return
    except discord.errors.DiscordServerError as e:
        return None

def same_vc(itr: Interaction, player: 'MusicPlayer'):
    if not itr.user.voice:
        return False
    if itr.user.voice.channel != player.channel:
        return False
    return True

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
    if not player or not player.guild:
        return

    guild = await music.bot.db.fetchone("SELECT * FROM music WHERE guild_id = %s", player.guild.id)

    if not guild:
        return

    await player.destroy()
    player.queue.clear()

    channel = player.guild.get_channel(guild['channel_id'])
    message = await get_message(channel, guild['message_id'], music.bot.db)
    queue_message = await get_message(channel, guild['queue_id'], music.bot.db)
    # message = await channel.fetch_message(guild['message_id'])
    # queue_message = await channel.fetch_message(guild['queue_id'])

    embed, embed2 = default_embed(music.view.bot)

    disabled_buttons(music.view.children)

    if not message.embeds or message.embeds[0].description != embed.description:
        await message.edit(embed=embed, view=music.view)

    if not queue_message.embeds or queue_message.embeds[0].description != embed2.description:
        await queue_message.edit(embed=embed2)

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
