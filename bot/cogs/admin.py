import discord
from discord.ext import commands
from discord import app_commands, Object
from typing import Literal, Optional

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="sync")
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        scope: Optional[Literal["current", "copy", "clear_local", "clear_global", "global"]] = "global",
        guilds: commands.Greedy[Object] = []
    ):
        tree = self.bot.tree
        guild = ctx.guild

        if guilds:
            success = 0
            for g in guilds:
                try:
                    await tree.sync(guild=g)
                    success += 1
                except Exception as e:
                    await ctx.send(f"Failed to sync to guild {g.id}: {e}")
            return await ctx.send(f"Synced to {success}/{len(guilds)} guild(s).")

        if scope == "current":
            synced = await tree.sync(guild=guild)
            return await ctx.send(f"Synced {len(synced)} command(s) to this guild ({guild.name}).")

        elif scope == "copy":
            tree.copy_global_to(guild=guild)
            synced = await tree.sync(guild=guild)
            return await ctx.send(f"Copied and synced {len(synced)} global command(s) to this guild ({guild.name}).")

        elif scope == "clear_local":
            tree.clear_commands(guild=guild)
            await tree.sync(guild=guild)
            return await ctx.send(f"Cleared all local commands from guild ({guild.name}).")

        elif scope == "clear_global":
            tree.clear_commands(guild=None)
            synced = await tree.sync()
            return await ctx.send(f"Cleared all global commands. {len(synced)} remain synced.")

        elif scope == "global":
            synced = await tree.sync()
            return await ctx.send(f"Synced {len(synced)} global command(s).")

        return await ctx.send("Invalid sync scope. Use: `current`, `copy`, `clear_local`, `clear_global`, or `global`.")

    @commands.command(name='resync')
    @commands.guild_only()
    @commands.is_owner()
    async def resync(self, ctx):
        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync()

        for guild in self.bot.guilds:
            self.bot.tree.clear_commands(guild=guild)
            await self.bot.tree.sync(guild=guild)

        for cog in self.bot._cogs:
            await self.bot.reload_extension(f"bot.cogs.{cog}")

        synced = await self.bot.tree.sync()
        await ctx.send(f"Resynced {len(synced)} global command(s).")

async def setup(bot):
    await bot.add_cog(Admin(bot))
