import discord
from discord import app_commands
from discord.ext import commands
from bot.cogs.views.games import ConfirmChallenge, MemoryView, RPSView, TicTacToeView

class GamesCommands(
    commands.GroupCog, name='games',
    description='**The Fun place where you and your friends can play games!**'
):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rock-paper-scissors", description="	Challenge a friend to a quick game of RPS!")
    async def rps(self, interaction: discord.Interaction, player2: discord.Member):
        if player2.bot:
            return await interaction.response.send_message("You can't challenge bots!", ephemeral=True)
        if player2 == interaction.user:
            return await interaction.response.send_message("You can't challenge yourself!", ephemeral=True)

        view = ConfirmChallenge(player2)
        await interaction.response.send_message(
            f"{player2.mention}, do you accept the RPS challenge from {interaction.user.mention}?",
            view=view
        )
        view.msg = interaction.original_response()
        await view.wait()

        if view.value == "yes":
            rps_view = RPSView(self.bot, interaction.user, player2, economy_enabled=self.bot.economy_enabled)
            msg = await interaction.channel.send(embed=rps_view.embed, view=rps_view)
            rps_view.message = msg
        elif view.value == "no":
            await interaction.edit_original_response(
                content=f"{player2.mention} declined the challenge.", view=None)
        else:
            await interaction.edit_original_response(
                content=f"{player2.mention} did not respond in time.", view=None)
            
    @app_commands.command(name="tic-tac-toe", description="	Play a classic 1v1 Tic Tac Toe match.")
    async def tictactoe(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.bot:
            return await interaction.response.send_message("You can't challenge bots!", ephemeral=True)
        if opponent == interaction.user:
            return await interaction.response.send_message("You can't challenge yourself!", ephemeral=True)

        confirm_view = ConfirmChallenge(opponent)
        await interaction.response.send_message(
            f"{opponent.mention}, do you accept the Tic Tac Toe challenge from {interaction.user.mention}?",
            view=confirm_view
        )
        await confirm_view.wait()

        if confirm_view.value == "yes":
            view = TicTacToeView(self.bot, interaction.user, opponent, economy_enabled=True)
            msg = await interaction.channel.send(embed=view.embed, view=view)
            view.message = msg
        elif confirm_view.value == "no":
            await interaction.edit_original_response(content=f"{opponent.mention} declined the challenge.", view=None)
        else:
            await interaction.edit_original_response(content=f"{opponent.mention} did not respond in time.", view=None)

    @app_commands.command(name="memory", description="Test your memory with an emoji matching puzzle game.")
    async def memory(self, interaction: discord.Interaction):
        view = MemoryView(self.bot, interaction.user)
        msg = await interaction.channel.send(embed=view.embed, view=view)
        view.message = msg

async def setup(bot):
    await bot.add_cog(GamesCommands(bot))
