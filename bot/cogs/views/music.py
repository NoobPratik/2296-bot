import asyncio
from io import StringIO
import re
from typing import TYPE_CHECKING, cast
import discord
from discord import Button, Interaction
from discord.ui import View
from pomice import Track
from pomice.enums import LoopMode
from bot.cogs.utils.music import MusicPlayer, get_duration

if TYPE_CHECKING:
    from bot import MyBot
    from bot.utils.database import Database
    from bot.cogs.music import Music

from bot.cogs.utils.music import (
    disabled_buttons, 
    enabled_buttons, 
    same_vc, 
)

class MusicButtons(View):
    def __init__(self, bot: 'MyBot', db: 'Database', parent: 'Music'):
        super().__init__(timeout=None)
        self.bot = bot
        self.db = db
        self.parent = parent
        self.error = discord.Embed(title='Error', colour=0xFF0000)
        self.success = discord.Embed(title='Success', colour=self.bot.color)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        player = cast(MusicPlayer, interaction.guild.voice_client)

        if not same_vc(interaction, player):
            self.error.description = 'You must be in the same VC to operate'
            await interaction.response.send_message(embed=self.error, ephemeral=True, delete_after=5)
            return False

        return True

    @discord.ui.button(emoji='<:Repeat:1158995878615453746>', custom_id='btn-repeat-song')
    async def repeat_song(self, itr: Interaction, _: Button):
        player = cast(MusicPlayer, itr.guild.voice_client)

        if player.queue.loop_mode == LoopMode.TRACK:
            player.queue.disable_loop()
            embed = discord.Embed(
                title='🔁 Loop Disabled',
                description='Stopped looping the current track.',
                color=discord.Color.red()
            )
            await itr.response.send_message(embed=embed, ephemeral=True, delete_after=5)
        else:
            player.queue.set_loop_mode(LoopMode.TRACK)
            self.success.description = 'Song loop ENABLED'
            embed = discord.Embed(
                title='🔂 Looping Current Song',
                description=f'Now looping: [{player.current.title}]({player.current.uri})',
                color=discord.Color.green()
            )
            await itr.response.send_message(embed=self.success, ephemeral=True, delete_after=5)

    @discord.ui.button(emoji='<:backward2white:1158995843857252472>', custom_id='btn-play-last')
    async def play_last(self, itr: Interaction, _: Button):
        await itr.response.defer()
        player = cast(MusicPlayer, itr.guild.voice_client)
        previous = self.parent.last_songs[-1] if self.parent.last_songs else None

        if not previous:
            msg = await itr.followup.send(content="`Looks like there's no song played before this one.`", ephemeral=True)
            await asyncio.sleep(10)
            return await msg.delete()

        player.current.info['play_last'] = True
        await player.stop()

    @discord.ui.button(emoji='<:Pause:1158995866221281331>', custom_id='btn-pause')
    async def play_pause(self, itr: Interaction, btn: Button):
        await itr.response.defer()
        player = cast(MusicPlayer, itr.guild.voice_client)

        if player.is_paused:
            self.success.description = 'Music Resumed'
            btn.emoji = '<:Pause:1158995866221281331>'
            await player.set_pause(False)
            await itr.edit_original_response(view=self)
            msg = await itr.followup.send(embed=self.success, ephemeral=True)
            await asyncio.sleep(5)
            return await msg.delete()
        
        self.success.description = 'Music Paused'
        btn.emoji = '<:Resume:1158995889591955466>'
        await player.set_pause(True)
        await itr.edit_original_response(view=self)
        msg = await itr.followup.send(embed=self.success, ephemeral=True)
        await asyncio.sleep(5)
        return await msg.delete()

    @discord.ui.button(emoji='<:forward2white:1158995848294838272>', custom_id='btn-play-next')
    async def play_next(self, itr: Interaction, _: Button):
        player = cast(MusicPlayer, itr.guild.voice_client)
        queue = player.queue.get_queue()
        song: Track = queue[0] if len(queue) != 0 else None
        await player.stop()

        embed = discord.Embed(
            title='⏭️ Song Skipped',
            description=f'**Next:** [{song.title}]({song.uri})' if song else 'No more songs in the queue.',
            color=self.bot.color
        )

        if song:
            embed.add_field(name="Duration", value=get_duration(song.length))
        if song and song.requester:
            embed.add_field(name="Requested by", value=str(song.requester.display_name) if song.requester else "")
            embed.set_thumbnail(url=song.thumbnail)

        await itr.response.send_message(embed=embed, ephemeral=True, delete_after=15)

    @discord.ui.button(emoji='<:RepeatPlaylist:1158995882918817883>', custom_id='btn-repeat-playlist')
    async def repeat_playlist(self, itr: Interaction, _: Button):
        player = cast(MusicPlayer, itr.guild.voice_client)

        if player.queue.loop_mode == LoopMode.QUEUE:
            player.queue.disable_loop()
            embed = discord.Embed(
                title='🔁 Playlist Loop Disabled',
                description='The playlist will no longer repeat once it ends.',
                color=discord.Color.red()
            )
            await itr.response.send_message(embed=embed, ephemeral=True, delete_after=5)
        else:
            player.queue.set_loop_mode(LoopMode.QUEUE)
            songs = len(player.queue.get_queue())
            embed = discord.Embed(
                title='🔁 Playlist Loop Enabled',
                description=f'The playlist ({songs} Songs) will now loop continuously.',
                color=discord.Color.green()
            )
            self.success.description = 'Playlist loop ENABLED'
            await itr.response.send_message(embed=self.success, ephemeral=True, delete_after=5)

    @discord.ui.button(emoji='<:VolumeDown:1158995920466235392>', custom_id='btn-volume-down')
    async def volume_down(self, itr: Interaction, _: Button):
        player = cast(MusicPlayer, itr.guild.voice_client)

        new_volume = max(player.volume - 10, 0)
        await player.set_volume(new_volume)

        self.success.description = f'Volume set to {new_volume}'
        await itr.response.send_message(embed=self.success, ephemeral=True, delete_after=5)

    @discord.ui.button(emoji='<:reverse:1158995896193785956>', custom_id='btn-reverse')
    async def reverse_queue(self, itr: Interaction, _: Button):
        player = cast(MusicPlayer, itr.guild.voice_client)

        reversed_songs = list(reversed(player.queue.get_queue()))
        player.queue.clear()
        player.queue.extend(reversed_songs)
        await player.update_queue(self.db)
        self.success.description = 'Queue Reversed'
        await itr.response.send_message(embed=self.success, delete_after=5, ephemeral=True)

    @discord.ui.button(emoji='<:cross:1158996277833506866>', custom_id='btn-destroy')
    async def destroy(self, itr: Interaction, _: Button):
        await itr.response.defer()
        player = cast(MusicPlayer, itr.guild.voice_client)
        await player.destroy()
        player.queue.clear()

        guild = await self.db.fetchone("SELECT * FROM music WHERE guild_id = %s", itr.guild.id)
        message = await itr.channel.fetch_message(guild['message_id'])
        queue_message = await itr.channel.fetch_message(guild['queue_id'])

        if not message or not queue_message:
            return

        embed, embed2 = player._get_embed()
        disabled_buttons(self.children)

        await message.edit(embed=embed, view=self)
        await queue_message.edit(embed=embed2)

    @discord.ui.button(emoji='<:Shuffle:1158995909636538458>', custom_id='btn-shuffle')
    async def shuffle(self, itr: Interaction, _: Button):
        await itr.response.defer()
        player = cast(MusicPlayer, itr.guild.voice_client)
        player.queue.shuffle()
        await player.update_queue(self.db)

    @discord.ui.button(emoji='<:VolumeUp:1158995926938046474>', custom_id='btn-volume-up')
    async def volume_up(self, itr: Interaction, _: Button):
        player = cast(MusicPlayer, itr.guild.voice_client)

        new_volume = min(player.volume + 10, 300)
        await player.set_volume(new_volume)
        self.success.description = f'Volume set to {new_volume}'
        await itr.response.send_message(embed=self.success, ephemeral=True, delete_after=5)

    @discord.ui.button(emoji='<:Lock:1158995859992744008>', custom_id='btn-lock')
    async def lock(self, itr: Interaction, btn: Button):
        await itr.response.defer()

        guild = await self.db.fetchone("SELECT * FROM music WHERE guild_id = %s", itr.guild.id)

        if guild['locked']:
            btn.emoji = '<Unlock:1158995915508564008>'
            self.success.description = 'Music Channel Unlocked'
            await self.db.execute("UPDATE music SET locked = %s WHERE guild_id = %s", False, itr.guild.id)
            enabled_buttons(self.children)
            await itr.edit_original_response(view=self)
            msg = await itr.followup.send(embed=self.success, ephemeral=True)
            await asyncio.sleep(5)
            return await msg.delete()

        else:
            btn.emoji = '<Lock:1158995859992744008>'
            self.success.description = 'Music Channel Locked'
            await self.db.execute("UPDATE music SET locked = %s WHERE guild_id = %s", True, itr.guild.id)
            disabled_buttons(self.children)
            await itr.edit_original_response(view=self)
            msg = await itr.followup.send(embed=self.success, ephemeral=True)
            await asyncio.sleep(5)
            return await msg.delete()

    @discord.ui.button(emoji='<:autoplay:1158995839117705235>', custom_id='btn-autoplay')
    async def autoplay(self, itr: Interaction, _: Button):
        player = cast(MusicPlayer, itr.guild.voice_client)

        if not player.autoplay:
            player.autoplay = True

            if player.queue.is_empty:
                await player.update_queue(self.db)

            self.success.description = 'AutoPlay enabled, this feature will add songs to the queue automatically'
            await itr.response.send_message(embed=self.success, ephemeral=True, delete_after=5)

        else:
            player.autoplay = False
            self.success.description = 'AutoPlay disabled, this feature will add songs to the queue automatically'
            await itr.response.send_message(embed=self.success, ephemeral=True, delete_after=5)

    @discord.ui.button(emoji='<:Like:1158995854661791794>', custom_id='btn-like-song')
    async def like_song(self, itr: Interaction, _: Button):
        await itr.response.defer()
        player = cast(MusicPlayer, itr.guild.voice_client)

        song = await self.db.fetchone(
            "SELECT song FROM favorite_music WHERE user_id = %s and song = %s",
            itr.user.id, player.current.identifier
        )

        if not song:
            await self.db.execute(
                "INSERT INTO favorite_music (song, user_id) VALUES (%s, %s)",
                player.current.identifier, itr.user.id
            )
            self.success.description = f'Successfully added {player.current.title} to liked songs'
            msg = await itr.followup.send(embed=self.success, ephemeral=True)
            await asyncio.sleep(5)
            return await msg.delete()

        await self.db.execute(
            "DELETE FROM favorite_music WHERE song = %s AND user_id = %s",
             player.current.identifier, itr.user.id
        )

        self.success.description = f'Successfully removed {player.current.title} from liked songs'
        msg = await itr.followup.send(embed=self.success, ephemeral=True)
        await asyncio.sleep(5)
        return await msg.delete()

    @discord.ui.button(emoji='<:lyrics:1394167977351450776>', custom_id='btn-lyric')
    async def lyrics(self, itr: Interaction, _: Button):
        await itr.response.defer(ephemeral=True, thinking=True)
        player = cast(MusicPlayer, itr.guild.voice_client)
        lyrics = await player._get_lyrics(skip_source=False)

        if lyrics:
            message = '\n'.join(x['line'] for x in lyrics)
            if len(message) <= 2000:
                await itr.followup.send(message, ephemeral=True)
            else:
                file = discord.File(fp=StringIO(message), filename="lyrics.txt")
                await itr.followup.send(
                    content="Lyrics were too long to display, so I've sent them as a file.",
                    file=file,
                    ephemeral=True
                )
        else:
            await itr.followup.send("No lyrics found.", ephemeral=True)

    @discord.ui.button(emoji='<:playliked:1158995871426433114>', custom_id='btn-play-liked')
    async def play_liked_songs(self, itr: Interaction, _: Button):
        await itr.response.defer()
        player = cast(MusicPlayer, itr.guild.voice_client)

        liked_music_list = await self.db.fetchall("SELECT * FROM favorite_music WHERE user_id = %s", itr.user.id)

        if not liked_music_list:
            msg = await itr.followup.send('Your liked song list is empty!', ephemeral=True)
            await asyncio.sleep(5)
            return await msg.delete()

        if not player:
            if not itr.user.voice:
                await itr.followup.send('You must be in a vc to listen to music', ephemeral=True)
                return

            player = await itr.user.voice.channel.connect(cls=MusicPlayer)

        if itr.user.voice.channel.id != player.channel.id:
            await itr.followup.send('You must be in the same vc to listen to music', ephemeral=True)
            return

        for item in liked_music_list:

            track: Track = player.build_track(item['song'])
            track.requester = itr.user

            await player.queue.put(track)
            if not player.is_playing:
                await player.play(player.queue.get())

        await player.update_queue(self.db)

        self.success.description = f'Added {len(liked_music_list)} Liked songs to the queue'
        msg = await itr.followup.send(embed=self.success, ephemeral=True)
        await asyncio.sleep(5)
        return await msg.delete()

class MusicClipModal(discord.ui.Modal, title='Song Timestamp'):
    def __init__(self, end_time):
        self.end_min, self.end_sec = map(int, end_time.split(':'))
        super().__init__(timeout=20)
        self.text = discord.ui.TextInput(
            label='Add Timestamp Example: 01:42 To 2:35',
            default=f'0:00 To {end_time}'
        )
        self.add_item(self.text)
        self.value = None

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer()  # noqa
        pattern = r'^(\d{1,2}:\d{2})\s*To\s*(\d{1,2}:\d{2})$'
        input_string = self.text.value
        match = re.match(pattern, input_string, re.IGNORECASE)

        if match:
            start_time = match.group(1)
            end_time = match.group(2)

            start_minute, start_second = map(int, start_time.split(':'))
            end_minute, end_second = map(int, end_time.split(':'))
            song_milliseconds = (self.end_min * 60 + self.end_sec) * 1000
            start_milliseconds = (start_minute * 60 + start_second) * 1000
            end_milliseconds = (end_minute * 60 + end_second) * 1000

            if start_milliseconds < end_milliseconds < song_milliseconds:
                msg = await interaction.followup.send(
                    f'Started song from {start_minute}:{start_second} To {end_minute}:{end_second}')
                self.value = [start_milliseconds, end_milliseconds]
                self.stop()
                await asyncio.sleep(5)
                return await msg.delete()

        msg = await interaction.followup.send('Incorrect Format, Please try again', ephemeral=True)
        await asyncio.sleep(5)
        await msg.delete()
        return self.stop()

    async def on_timeout(self) -> None:
        self.stop()
