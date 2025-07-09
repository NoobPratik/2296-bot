from typing import Literal, Optional
import discord
from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.bot import MyBot

class Admin(commands.Cog):
    def __init__(self, bot: 'MyBot'):
        super().__init__()
        self.bot = bot

    @commands.command(name="sync")
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        scope: Optional[Literal["current", "copy", "clear_local", "clear_global", "global"]] = "global",
        guilds: commands.Greedy[discord.Object] = []
    ) -> None:
        """
        Sync application commands (slash commands).
        
        Parameters:
        - current: Sync to the current guild.
        - copy: Copy global commands to current guild and sync.
        - clear_local: Clear commands from current guild.
        - clear_global: Clear global commands.
        - global (default): Sync commands globally.
        """

        # If syncing to specified guilds
        if guilds:
            success = 0
            for guild in guilds:
                try:
                    await self.bot.tree.sync(guild=guild)
                    success += 1
                except discord.HTTPException as e:
                    await ctx.send(f"Failed to sync to guild `{guild.id}`: {e}")
            return await ctx.send(f"Synced commands to {success}/{len(guilds)} guilds.")

        guild = ctx.guild
        if scope == "current":
            synced = await self.bot.tree.sync(guild=guild)
            return await ctx.send(f"✅ Synced {len(synced)} commands to **this guild** (`{guild.name}`)")

        elif scope == "copy":
            self.bot.tree.copy_global_to(guild=guild)
            synced = await self.bot.tree.sync(guild=guild)
            return await ctx.send(f"✅ Copied and synced {len(synced)} global commands to **this guild**")

        elif scope == "clear_local":
            self.bot.tree.clear_commands(guild=guild)
            await self.bot.tree.sync(guild=guild)
            return await ctx.send(f"🧹 Cleared all **local** commands from this guild (`{guild.name}`)")

        elif scope == "clear_global":
            self.bot.tree.clear_commands(guild=None)
            synced = await self.bot.tree.sync()
            return await ctx.send(f"🧹 Cleared all **global** commands. {len(synced)} commands remain synced.")

        elif scope == "global":
            synced = await self.bot.tree.sync()
            return await ctx.send(f"🌍 Synced {len(synced)} commands **globally**")

        else:
            return await ctx.send("❌ Invalid sync scope. Please use one of: `current`, `copy`, `clear_local`, `clear_global`, or `global`.")


async def setup(bot):
    await bot.add_cog(Admin(bot))