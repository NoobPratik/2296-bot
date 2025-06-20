import asyncio
from enum import Enum
import random
from discord.ui import View, button
import discord
from discord import Interaction, ButtonStyle, InteractionMessage

class ConfirmChallenge(View):
    def __init__(self, challenger: discord.User):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.value = None
        self.msg: InteractionMessage = None

    @button(label="Accept", style=ButtonStyle.success)
    async def accept(self, interaction: Interaction, _):
        if interaction.user != self.challenger:
            await interaction.response.send_message("This isn't for you!", ephemeral=True)
            return
        self.value = "yes"
        self.stop()
        await interaction.delete_original_response()

    @button(label="Decline", style=ButtonStyle.danger)
    async def decline(self, interaction: Interaction, _):
        if interaction.user != self.challenger:
            await interaction.response.send_message("This isn't for you!", ephemeral=True)
            return
        self.value = "no"
        self.stop()
        await interaction.delete_original_response()

    async def on_timeout(self):
        self.value = "timeout"
        if self.msg:
            await self.msg.delete()

class RPSChoice(Enum):
    ROCK = "Rock"
    PAPER = "Paper"
    SCISSORS = "Scissors"

    def beats(self, other):
        return (
            (self == RPSChoice.ROCK and other == RPSChoice.SCISSORS) or
            (self == RPSChoice.SCISSORS and other == RPSChoice.PAPER) or
            (self == RPSChoice.PAPER and other == RPSChoice.ROCK)
        )

EMOJI_MAP = {
    RPSChoice.ROCK: "🪨",
    RPSChoice.PAPER: "📄",
    RPSChoice.SCISSORS: "✂️"
}

WIN_GIFS = [
    "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGxzY29mdWQ5bnIyd2J3Nmx6dmprYm8zbjM3ajBneHd6MTRqNDF1NiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/o75ajIFH0QnQC3nCeD/giphy.gif",
    "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExeGtkcWpyeHZ1Y2x4OGk0M3RlenVpNXNxZGVybTc1NTQzdXJnMm5nYiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/DmzQ4iPMyUScw/giphy.gif",
    "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExNGw2eW5zam1wdHpocGNpcXQyeWJrcXZtdHhjeG0wOG53N2k1OGtoYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/boNNxI4tHdez3kThsn/giphy.gif",
    "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExeHlqZ3Bvb2N4a2U5ZXJwZ2xycm13dHh4cG5sOGV2NWx3Ynoxb3l1NSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/gd0Dqg6rYhttBVCZqd/giphy.gif"
]

DRAW_GIFS = [
    "https://tenor.com/MgLe.gif",
    "https://tenor.com/rIXPeyz72QA.gif",
    "https://tenor.com/bC6Uh.gif",
    "https://tenor.com/bS6aF.gif"
]

class RPSView(discord.ui.View):
    def __init__(self, bot, user1: discord.User, user2: discord.User, economy_enabled=False):
        super().__init__(timeout=120)
        self.bot = bot
        self.user1 = user1
        self.user2 = user2
        self.economy_enabled = economy_enabled
        self.choices = {user1.id: None, user2.id: None}
        self.embed = discord.Embed(
            title=f"🎮 Rock Paper Scissors - {user1.name} vs {user2.name}",
            color=discord.Color.purple(),
            description=f"{user1.mention} and {user2.mention} are making their moves..."
        )
        self.embed.set_footer(text="Game started", icon_url=bot.user.avatar.url)

    async def disable_all(self):
        for child in self.children:
            child.disabled = True

    async def finish_game(self, interaction: Interaction):
        await self.disable_all()
        p1_choice = self.choices[self.user1.id]
        p2_choice = self.choices[self.user2.id]

        desc = (
            f"✨ {self.user1.mention} chose {EMOJI_MAP[p1_choice]} **{p1_choice.value}**\n"
            f"✨ {self.user2.mention} chose {EMOJI_MAP[p2_choice]} **{p2_choice.value}**\n\n"
        )

        winner = None
        if p1_choice == p2_choice:
            result = "📊 It's a draw!"
            self.embed.color = discord.Color.gold()
            self.embed.set_image(url=random.choice(DRAW_GIFS))
        elif p1_choice.beats(p2_choice):
            winner = self.user1
            result = f"🏆 {self.user1.name} wins!"
            self.embed.color = discord.Color.green()
            self.embed.set_image(url=random.choice(WIN_GIFS))
        else:
            winner = self.user2
            result = f"🏆 {self.user2.name} wins!"
            self.embed.color = discord.Color.red()
            self.embed.set_image(url=random.choice(WIN_GIFS))

        if self.economy_enabled and winner:
            reward = await self.economy.reward(winner.id)
            desc += f"\n🎁 {winner.mention} received **{reward} Spider Coins**!"

        self.embed.description = desc
        self.embed.set_footer(text=result, icon_url=(winner.avatar.url if winner else self.bot.user.avatar.url))
        await interaction.edit_original_response(embed=self.embed, view=self)

    async def handle_choice(self, interaction: discord.Interaction, choice: RPSChoice):
        if interaction.user.id not in self.choices:
            await interaction.response.send_message("You're not part of this game!", ephemeral=True)
            return

        self.choices[interaction.user.id] = choice
        await interaction.response.defer()

        self.embed.description = (
            f"{self.user1.name}: {'✅' if self.choices[self.user1.id] else '❓'}\n"
            f"{self.user2.name}: {'✅' if self.choices[self.user2.id] else '❓'}"
        )
        await interaction.edit_original_response(embed=self.embed, view=self)

        if all(self.choices.values()):
            await self.finish_game(interaction)

    @discord.ui.button(label="Rock", style=ButtonStyle.green)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, RPSChoice.ROCK)

    @discord.ui.button(label="Paper", style=ButtonStyle.blurple)
    async def paper(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.handle_choice(interaction, RPSChoice.PAPER)

    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.red)
    async def scissors(self, interaction: Interaction, _: discord.ui.Button):
        await self.handle_choice(interaction, RPSChoice.SCISSORS)

    async def on_timeout(self):
        if not all(self.choices.values()):
            await self.disable_all()
            self.embed.color = discord.Color.dark_gray()
            self.embed.set_footer(text="Game timed out! 😴")
            self.embed.description = "One or more players didn't respond in time."
            await self.message.edit(embed=self.embed, view=self)

class TicTacToeView(discord.ui.View):
    def __init__(self, bot, player1: discord.Member, player2: discord.Member, economy_enabled=False):
        super().__init__(timeout=120)
        self.bot = bot
        self.players = [player1, player2]
        random.shuffle(self.players)
        self.turn = 0  # index in self.players
        self.board = [None] * 9
        self.symbols = ["⭕", "❌"]
        self.economy_enabled = economy_enabled
        self.message = None
        self.finished = False

        for i in range(9):
            row = i // 3
            col = i % 3
            self.add_item(self.TicTacToeButton(i, row, col))

        self.embed = discord.Embed(
            title=f"Tic Tac Toe - {self.players[0].name} vs {self.players[1].name}",
            description=f"{self.players[self.turn].mention}'s turn {self.symbols[self.turn]}",
            color=discord.Color.blurple()
        )

    class TicTacToeButton(discord.ui.Button):
        def __init__(self, index, row, col):
            super().__init__(style=discord.ButtonStyle.secondary, label="​", row=row, custom_id=str(index))
            self.index = index

        async def callback(self, interaction: discord.Interaction):
            view: TicTacToeView = self.view

            if view.finished:
                return await interaction.response.send_message("This game is already over.", ephemeral=True)

            current_player = view.players[view.turn]
            if interaction.user != current_player:
                return await interaction.response.send_message("It's not your turn!", ephemeral=True)

            if view.board[self.index] is not None:
                return await interaction.response.send_message("This spot is already taken!", ephemeral=True)

            symbol = view.symbols[view.turn]
            self.label = symbol
            self.style = discord.ButtonStyle.green if view.turn == 0 else discord.ButtonStyle.red
            self.disabled = True

            view.board[self.index] = view.turn

            if view.check_winner():
                winner = view.players[view.turn]
                view.embed.description = f"🏆 {winner.mention} wins the game!"
                view.embed.color = discord.Color.green() if view.turn == 0 else discord.Color.red()
                if view.economy_enabled:
                    reward = await view.economy.reward(winner.id)
                    view.embed.description += f"\n🎁 {winner.mention} receives {reward} Spider Coins!"
                view.finished = True
                for child in view.children:
                    child.disabled = True
                await interaction.response.edit_message(embed=view.embed, view=view)
                return

            elif all(space is not None for space in view.board):
                view.embed.description = "It's a draw!"
                view.embed.color = discord.Color.gold()
                view.finished = True
                for child in view.children:
                    child.disabled = True
                await interaction.response.edit_message(embed=view.embed, view=view)
                return

            view.turn ^= 1
            view.embed.description = f"{view.players[view.turn].mention}'s turn {view.symbols[view.turn]}"
            await interaction.response.edit_message(embed=view.embed, view=view)

    def check_winner(self):
        b = self.board
        patterns = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
            (0, 3, 6), (1, 4, 7), (2, 5, 8),  # columns
            (0, 4, 8), (2, 4, 6)              # diagonals
        ]
        for i, j, k in patterns:
            if b[i] == b[j] == b[k] and b[i] is not None:
                return True
        return False

    async def on_timeout(self):
        if self.finished:
            return
        self.embed.description = "Game timed out due to inactivity."
        self.embed.color = discord.Color.dark_gray()
        for child in self.children:
            child.disabled = True
        await self.message.edit(embed=self.embed, view=self)

class MemoryView(discord.ui.View):
    def __init__(self, bot, player: discord.User):
        super().__init__(timeout=180)
        self.bot = bot
        self.player = player
        self.economy = None
        self.memory_dict = self.generate_board()
        self.revealed = []
        self.score = 0
        self.moves_left = 20
        self.finished = False
        self.message = None
        self.last_button = None

        stats_btn = discord.ui.Button(label=str(self.moves_left), style=discord.ButtonStyle.red, disabled=True, row=0)
        self.stats_button = stats_btn
        self.add_item(stats_btn)

        for i in range(24):
            index = i + 1
            row = index // 5
            self.add_item(self.MemoryButton(str(i), row=row))

        self.embed = discord.Embed(
            title=f"🧠 Memory Game - {player.name}",
            description="Flip and match the emojis!",
            color=discord.Color.purple()
        )

    def generate_board(self):
        emojis = [
            "🍕", "🍉", "🍎", "🍓", "🍇", "🍌",
            "🍒", "🍍", "🥝", "🍋", "🥥", "🥭"
        ] * 2  # 24 emojis
        random.shuffle(emojis)
        return {str(i): emojis[i] for i in range(24)}

    class MemoryButton(discord.ui.Button):
        def __init__(self, custom_id, row):
            super().__init__(
                style=discord.ButtonStyle.secondary,
                emoji="⬛",
                row=row,
                custom_id=custom_id
            )

        async def callback(self, interaction: discord.Interaction):
            view: MemoryView = self.view

            if interaction.user != view.player:
                return await interaction.response.send_message("This is not your game!", ephemeral=True)

            if self.custom_id in view.revealed:
                return await interaction.response.send_message("You've already matched this tile!", ephemeral=True)

            await interaction.response.defer()

            self.emoji = view.memory_dict[self.custom_id]
            self.style = discord.ButtonStyle.blurple
            self.disabled = True
            await interaction.edit_original_response(embed=view.embed, view=view)

            if view.last_button is not None:
                second = self
                first = view.last_button
                view.last_button = None

                if view.memory_dict[first.custom_id] == view.memory_dict[second.custom_id]:
                    first.style = discord.ButtonStyle.success
                    second.style = discord.ButtonStyle.success
                    view.revealed.extend([first.custom_id, second.custom_id])
                    view.score += 1
                    if view.score == 12:
                        view.finished = True
                        reward = await view.economy.reward(view.player.id, 120)
                        view.embed.description = f"🎉 {view.player.mention}, you matched all pairs!\n🎁 You earned {reward} Spider Coins."
                        for child in view.children:
                            child.disabled = True
                        view.add_item(PlayAgainButton(view.bot))
                        return await interaction.edit_original_response(embed=view.embed, view=view)
                else:
                    await asyncio.sleep(1)
                    first.emoji = "⬛"
                    second.emoji = "⬛"
                    first.style = discord.ButtonStyle.secondary
                    second.style = discord.ButtonStyle.secondary
                    first.disabled = False
                    second.disabled = False

                view.moves_left -= 1
                view.stats_button.label = f"{view.moves_left}"

                if view.moves_left == 0:
                    view.finished = True
                    view.embed.description = f"😵 {view.player.mention}, you're out of moves! You matched {view.score} pairs."
                    for child in view.children:
                        child.disabled = True
                    view.add_item(PlayAgainButton(view.bot))
                    return await interaction.edit_original_response(embed=view.embed, view=view)

                await interaction.edit_original_response(embed=view.embed, view=view)
            else:
                view.last_button = self

    async def on_timeout(self):
        if self.finished:
            return
        self.embed.description = f"⏰ Time's up, {self.player.mention}! You matched {self.score} pairs."
        for child in self.children:
            child.disabled = True
        await self.message.edit(embed=self.embed, view=self)


class PlayAgainButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="🔁 Play Again", style=discord.ButtonStyle.primary)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = MemoryView(self.bot, interaction.user)
        msg = await interaction.channel.send(embed=view.embed, view=view)
        view.message = msg