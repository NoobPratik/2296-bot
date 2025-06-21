import logging
import sys
import traceback
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

log = logging.getLogger(__name__)

class Errors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_error_to_webhook(self, embed: discord.Embed):
        try:
            await self.bot.webhook.send(embed=embed)
        except Exception as e:
            log.warning(f"Failed to send error to webhook: {e}")

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, (discord.Forbidden, discord.NotFound, app_commands.CommandNotFound)):
            return

        if hasattr(error, "original"):
            error = error.original

        if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
            if not interaction.response.is_done():
                await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Slash Command Error",
            color=0xFF5555,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="User", value=f"{interaction.user} (ID: {interaction.user.id})", inline=False)
        embed.add_field(name="Command", value=f"/{interaction.command.name}", inline=False)
        embed.add_field(name="Guild", value=str(interaction.guild) if interaction.guild else "DMs", inline=False)

        trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        embed.description = f"```py\n{trace[-1000:]}```"

        await self.send_error_to_webhook(embed)

    async def on_generic_error(self, event, *args, **kwargs):
        exc_type, exc, tb = sys.exc_info()
        trace = "".join(traceback.format_exception(exc_type, exc, tb))

        embed = discord.Embed(
            title="Event Error",
            color=0xAA3366,
            description=f"```py\n{trace[-1000:]}```",
            timestamp=datetime.now()
        )
        embed.add_field(name="Event", value=event)

        await self.send_error_to_webhook(embed)


old_on_error = commands.Bot.on_error


async def custom_on_error(self, event, *args, **kwargs):
    cog = self.get_cog("errors")
    if cog:
        await cog.on_generic_error(event, *args, **kwargs)


async def setup(bot):
    await bot.add_cog(Errors(bot))
    commands.Bot.on_error = custom_on_error


async def teardown(bot):
    commands.Bot.on_error = old_on_error
