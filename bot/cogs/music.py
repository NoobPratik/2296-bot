import re
from typing import cast
import discord
from discord import app_commands
from discord.ext import commands
from pomice import Player, SearchType, Track
import pomice
from typing import TYPE_CHECKING
from bot.cogs.utils.music import (
    MusicPlayer,
    default_embed, 
    disabled_buttons, 
    now_playing,
    reset_embeds, 
    update_queue,
)
from bot.cogs.views.music import MusicButtons

if TYPE_CHECKING:
    from bot import MyBot
    from bot.utils.database import Database

class Music(commands.Cog, name='music', description='Play, Skip, Seek and more using the music commands'):
    def __init__(self, bot: 'MyBot'):
        self.bot = bot
        self.db: 'Database' = self.bot.db
        self.view = MusicButtons(bot, db=self.db, parent=self)
        self.channels = []
        self.last_songs = []
        self.emoji_guide = (
            "\nMusic Controls:\n"
            "<:Repeat:1158995878615453746> Repeat Song | "
            "<:Lock:1158995859992744008> Lock | "
            "<:RepeatPlaylist:1158995882918817883> Repeat Queue\n"

            "<:reverse:1158995896193785956> Reverse Queue | "
            "<:autoplay:1158995839117705235> Autoplay | "
            "<:Shuffle:1158995909636538458> Shuffle\n"

            "<:playliked:1158995871426433114> Play Liked | "
            "<:Like:1158995854661791794> Like | "
            "<:lyrics:1394167977351450776> Lyrics\n"
        )

    @app_commands.command(name='music-setup', description='Create a music channel for you to play and control music.')
    async def _setup(self, itr: discord.Interaction, channel: discord.TextChannel = None):
        await itr.response.defer()
        state = await self.db.fetchone("SELECT channel_id FROM music WHERE guild_id = %s", itr.guild.id)

        if state and state['channel_id']:
            existing_channel = itr.guild.get_channel(state['channel_id'])
            if existing_channel:
                embed = discord.Embed(
                    title='Music Channel Already Exists',
                    color=0xFF0000,
                    description=f'Channel: {itr.guild.get_channel(state["channel_id"]).mention}'
                )
                embed.set_footer(text='Use /music-destroy to remove the channel')
                return await itr.followup.send(embed=embed, ephemeral=True)
            
        if not channel:
            channel = await itr.guild.create_text_channel(name='2296 Song-Requests', topic=self.emoji_guide)
        else:
            await channel.edit(topic=self.emoji_guide)

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
                await message.channel.send('Please join a voice channel to use music features.', delete_after=5)
                return await message.delete()

            try:
                player = await message.author.voice.channel.connect(cls=MusicPlayer)
            except pomice.exceptions.NodeNotAvailable:
                await message.channel.send('The music service is currently unavailable. Please try again shortly.', delete_after=10)
                return await message.delete()

        if guild['locked']:
            if player.playing:
                await message.channel.send("The music channel is locked. Adding new songs is temporarily disabled.", delete_after=5)
                return await message.delete()
            await self.db.execute("UPDATE music SET locked = %s WHERE guild_id = %s", False, message.guild.id)

        try:
            is_spotify = re.match(r'https?://open.spotify.com/(?P<type>album|playlist|track|artist)/(?P<id>[a-zA-Z0-9]+)', message.content)
            search_type = None if is_spotify else SearchType.ytmsearch
            tracks = await player.get_tracks(message.content, search_type=search_type)
        except Exception as e:
            print(repr(e))

        if not tracks:
            await message.channel.send(f"No matching tracks were found. Please refine your search and try again.", delete_after=5)
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
        if channel.id not in self.channels:
            return

        await self.bot.db.execute(
            "DELETE FROM music WHERE channel_id = %s AND guild_id = %s",
            channel.id, channel.guild.id
        )

        if isinstance(channel, discord.VoiceChannel):
            player = self.bot.pomice.get_best_node().get_player(channel.guild.id)
            if player and player.channel and player.channel.id == channel.id:
                await reset_embeds(player)



async def setup(bot):
    await bot.add_cog(Music(bot))