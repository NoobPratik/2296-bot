import asyncio
import re
from typing import cast
import discord
from discord import Button, Interaction, app_commands
from discord.ext import commands
from discord.ui import View
from pomice import Player, Queue, SearchType, Track
from pomice.enums import LoopMode
import pomice
from typing import TYPE_CHECKING
from bot.cogs.utils.music import (
    default_embed, 
    disabled_buttons, 
    enabled_buttons, 
    get_duration,
    now_playing,
    reset_embeds, 
    same_vc, 
    update_queue,
)

if TYPE_CHECKING:
    from bot import MyBot
    from bot.utils.database import Database

class MusicPlayer(Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.autoplay = False
        self.queue = Queue()

class Music(commands.Cog, name='music', description='Play, Skip, Seek and more using the music commands'):
    def __init__(self, bot: 'MyBot'):
        self.bot = bot
        self.db: 'Database' = self.bot.db
        self.view = MusicButtons(bot, db=self.db, parent=self)
        self.channels = []
        self.last_songs = []

    @app_commands.command(name='music-setup', description='Create a music channel for you to play and control music.')
    async def _setup(self, itr: discord.Interaction):
        await itr.response.defer()

        state = await self.db.fetchone("SELECT channel_id FROM music WHERE guild_id = %s", itr.guild.id)

        if state and state['channel_id']:
            channel = itr.guild.get_channel(state['channel_id'])
            if channel:
                embed = discord.Embed(
                    title='Music Channel Already Exists',
                    color=0xFF0000,
                    description=f'Channel: {itr.guild.get_channel(state["channel_id"]).mention}'
                )
                embed.set_footer(text='Use /music-destroy to remove the channel')
                return await itr.followup.send(embed=embed, ephemeral=True)
            
        channel = await itr.guild.create_text_channel(name='2296 Song-Requests')
        self.channels.append(channel.id)
        embed, embed2 = default_embed(self.bot)
        disabled_buttons(self.view.children)

        queue_message = await channel.send(embed=embed2)
        song_msg = await channel.send(embed=embed, view=self.view)

        await itr.followup.send(embed=discord.Embed(
            title='Successfully Created Music channel',
            color=0x00ff00,
            description=channel.mention)
        )
        
        guild = await self.db.fetchone("SELECT guild_id FROM music WHERE guild_id = %s", itr.guild.id)
        
        if not guild:
            await self.db.execute(
                "INSERT INTO music (guild_id, channel_id, message_id, queue_id) VALUES (%s,%s,%s,%s)",
                itr.guild.id, channel.id, song_msg.id, queue_message.id
            )

        else:
            await self.db.execute(
                "UPDATE music SET channel_id=%s, message_id=%s, queue_id=%s",
                channel.id, song_msg.id, queue_message.id
            )

    @commands.Cog.listener()
    async def on_pomice_track_start(self, player: Player, _: Track):
        await now_playing(self, player)

    @commands.Cog.listener()
    async def on_pomice_track_end(self, player: MusicPlayer, old_track: Track, _: str):

        if not player.queue.loop_mode:
            self.last_songs.append(old_track.identifier)

        next_track = None
        try:
            next_track = player.queue.get()

        except pomice.exceptions.QueueEmpty:
            return await reset_embeds(self, player)
                    
        await update_queue(self.bot, self.db, player)
        return await player.play(next_track)

    @commands.Cog.listener()
    async def on_pomice_track_exception(self, data: dict, player: MusicPlayer):
        print(data)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.channel.id not in self.channels:
            return 
            
        if message.author.bot:
            return

        guild = await self.db.fetchone("SELECT * FROM music WHERE guild_id = %s", message.guild.id)
        if not guild:
            return

        player: MusicPlayer
        player = cast(MusicPlayer, message.guild.voice_client)
        if not player:
            if not message.author.voice:
                await message.channel.send('You must be in a vc to listen to music', delete_after=5)
                return

            player = await message.author.voice.channel.connect(cls=MusicPlayer)

        if guild['locked']:
            if player.playing:
                await message.channel.send("Currently locked, cannot add anymore songs.", delete_after=5)
                return await message.delete()
            await self.db.execute("UPDATE music SET locked = %s WHERE guild_id = %s", False, message.guild.id)

        try:
            is_spotify = re.match(r'https?://open.spotify.com/(?P<type>album|playlist|track|artist)/(?P<id>[a-zA-Z0-9]+)', message.content)
            search_type = None if is_spotify else SearchType.ytmsearch
            tracks = await player.get_tracks(message.content, search_type=search_type)
        except Exception as e:
            print(repr(e))

        if not tracks:
            await message.channel.send(f"Could not find any tracks with that query. Please try again.", delete_after=5)
            return
        
        if isinstance(tracks, pomice.objects.Playlist):
            for track in tracks.tracks:
                track.requester = message.author
            player.queue.extend(tracks.tracks)
        else:
            track: Track = tracks[0]
            track.requester = message.author
            player.queue.put(track)

        if not player.is_playing:
            await player.play(player.queue.get())

        await update_queue(bot=self.bot, db=self.db, player=player)
        await message.delete()

    @commands.Cog.listener()
    async def on_ready(self):
        guilds = await self.db.fetchall("SELECT * FROM music WHERE message_id IS NOT NULL")
        for guild in guilds:
            channel = self.bot.get_channel(guild['channel_id'])

            if not channel:
                return
            self.channels.append(channel.id)

            message = await channel.fetch_message(guild['message_id'])
            queue_message = await channel.fetch_message(guild['queue_id'])

            if not message or not queue_message:
                return

            embed, embed2 = default_embed(self.bot)
            disabled_buttons(self.view.children)

            if message.embeds and message.embeds[0].description != embed.description:
                await message.edit(embed=embed, view=self.view)
            if queue_message.embeds and queue_message.embeds[0].description != embed2.description:
                await queue_message.edit(embed=embed2)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        player = cast(MusicPlayer, member.guild.voice_client)

        if member.id == self.bot.user.id:
            if before.channel and not after.channel:
                if player:
                    await reset_embeds(self, player)
                return

        if not player or not player.channel:
            return

        if before.channel and before.channel == player.channel:
            remaining = [m for m in player.channel.members if not m.bot]
            if not remaining:
                await reset_embeds(self, player)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        db_channel = await self.bot.db.fetchone(
            "SELECT * FROM music WHERE channel_id = %s AND guild_id = %s",
            channel.id, channel.guild.id
        )

        if db_channel:
            await self.bot.db.execute(
                "DELETE FROM music WHERE channel_id = %s AND guild_id = %s",
                channel.id, channel.guild.id
            )

        if isinstance(channel, discord.VoiceChannel):
            player = self.bot.pomice.get_best_node().get_player(channel.guild.id)
            if player and player.channel and player.channel.id == channel.id:
                await reset_embeds(player)


class MusicButtons(View):
    def __init__(self, bot: 'MyBot', db: 'Database', parent: Music):
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
            self.success.description = 'Song loop DISABLED'
            await itr.response.send_message(embed=self.success, ephemeral=True, delete_after=5)
        else:
            player.queue.set_loop_mode(LoopMode.TRACK)
            self.success.description = 'Song loop ENABLED'
            await itr.response.send_message(embed=self.success, ephemeral=True, delete_after=5)

    @discord.ui.button(emoji='<:backward2white:1158995843857252472>', custom_id='btn-play-last')
    async def play_last(self, itr: Interaction, _: Button):
        await itr.response.defer()
        player = cast(MusicPlayer, itr.guild.voice_client)

        previous = self.parent.last_songs[-1] if self.parent.last_songs else None
        if not previous:
            self.error.description = 'No previous song found'
            msg = await itr.followup.send(embed=self.error, ephemeral=True)
            await asyncio.sleep(5)
            return await msg.delete()

        await player.play(previous)

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

        await player.stop()
        self.success.description = 'Song Skipped'
        await itr.response.send_message(embed=self.success, ephemeral=True, delete_after=5)

    @discord.ui.button(emoji='<:RepeatPlaylist:1158995882918817883>', custom_id='btn-repeat-playlist')
    async def repeat_playlist(self, itr: Interaction, _: Button):
        player = cast(MusicPlayer, itr.guild.voice_client)

        if player.queue.loop_mode == LoopMode.QUEUE:
            player.queue.disable_loop()
            self.success.description = 'Playlist loop DISABLED'
            await itr.response.send_message(embed=self.success, ephemeral=True, delete_after=5)
        else:
            player.queue.set_loop_mode(LoopMode.QUEUE)
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
        await update_queue(bot=self.bot, db=self.db, player=player)
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

        embed, embed2 = default_embed(self.bot)
        disabled_buttons(self.children)

        await message.edit(embed=embed, view=self)
        await queue_message.edit(embed=embed2)

    @discord.ui.button(emoji='<:Shuffle:1158995909636538458>', custom_id='btn-shuffle')
    async def shuffle(self, itr: Interaction, _: Button):
        await itr.response.defer()
        player = cast(MusicPlayer, itr.guild.voice_client)
        player.queue.shuffle()
        await update_queue(bot=self.bot, db=self.db, player=player)

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
                await update_queue(self.bot, self.db, player)

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

    @discord.ui.button(emoji='<:scissors:1158995902443302973>', custom_id='btn-clip')
    async def clip(self, itr: Interaction, _: Button):
        player = cast(MusicPlayer, itr.guild.voice_client)
        modal = MusicClipModal(get_duration(player.current.length))
        await itr.response.send_modal(modal)
        await modal.wait()
        if modal.value:
            start, end = modal.value
            player.current.info['start'] = start
            player.current.info['end'] = end
            await player.play(player.current, start=start, end=end)

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

        await update_queue(bot=self.bot, db=self.db, player=player)

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

async def setup(bot):
    await bot.add_cog(Music(bot))