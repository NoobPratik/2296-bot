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

    async def on_error(self, itr: discord.Interaction, error):
        print('error occured')
        await self.register_command(itr, is_error=error)
        if isinstance(error, app_commands.CommandNotFound):
            return

        if hasattr(error, 'original'):
            error = error.original

        if isinstance(error, (discord.Forbidden, discord.NotFound)):
            return

        elif isinstance(error, app_commands.MissingPermissions):
            if itr.response.is_done():
                return

            await itr.response.send_message(f'You do not have permission to use this command.', ephemeral=True)
            return

        elif isinstance(error, app_commands.CheckFailure):
            if itr.response.is_done():
                return

            if not itr.guild:
                return await itr.response.send_message(
                    'You cannot use this command in a private message.', ephemeral=True
                )
            return await itr.response.send_message(f"You are not allowed to use this command.", ephemeral=True)
        elif isinstance(error, RuntimeError):
            return await itr.response.send_message(
                'Sorry, There is a problem with runtime! Please try again later.', ephemeral=True
            )

        e = discord.Embed(title='Command Error', colour=0xcc3366)
        if itr.namespace:
            cmd = itr.command.name
            if itr.message:
                if hasattr(itr.message, 'interaction'):
                    cmd = itr.message.interaction.name

            ns = ''
            try:
                for key, value in itr.namespace:
                    ns += f'{key}: {value} '
            except (TypeError, ValueError, AttributeError):
                pass

            e.add_field(
                name='Slash Command',
                value=f"/{cmd} {ns}",
            )
        if hasattr(itr.command, 'type'):
            e.add_field(name='Type', value=itr.command.type)
        e.add_field(name='Author', value=f'{itr.user} (ID: {itr.user.id})')

        fmt = f'Channel: {itr.channel} (ID: {itr.channel.id})'
        if itr.guild:
            fmt = f'{fmt}\nGuild: {itr.guild} (ID: {itr.guild.id})'

        e.add_field(name='Location', value=fmt, inline=False)
        # e.add_field(name='Content', value=textwrap.shorten(itr.message.content, width=512))

        exc = ''.join(traceback.format_exception(type(error), error, error.__traceback__, chain=False))
        e.description = f'```py\n{exc}\n```'
        e.timestamp = datetime.now()
        await self.bot.webhook.send(embed=e)

old_on_error = commands.Bot.on_error
old_on_command_error = app_commands.CommandTree.on_error

async def on_error(self, event, *args, **kwargs):
    (exc_type, exc, tb) = sys.exc_info()
    if isinstance(exc, app_commands.CommandInvokeError):
        return
    print('error occured')
    e = discord.Embed(title='Event Error', colour=0xa32952)
    e.add_field(name='Event', value=event)
    trace = "".join(traceback.format_exception(exc_type, exc, tb))
    e.description = f'```py\n{trace}\n```'
    e.timestamp = datetime.utcnow()

    args_str = ['```py']
    for index, arg in enumerate(args):
        args_str.append(f'[{index}]: {arg!r}')
    args_str.append('```')
    e.add_field(name='Args', value='\n'.join(args_str), inline=False)
    hook = self.webhook
    try:
        await hook.send(embed=e)
    except Exception as e:
        log.debug(f'Failed to send error to webhook: {e}')

async def setup(bot):
    cog = Errors(bot)
    await bot.add_cog(cog)

    commands.Bot.on_error = on_error
    app_commands.CommandTree.on_error = cog.on_error


async def teardown(bot):
    commands.Bot.on_error = old_on_error
    app_commands.CommandTree.on_error = old_on_command_error
