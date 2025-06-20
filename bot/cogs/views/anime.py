from datetime import datetime
import discord
import pytz
from bot.cogs.utils.anime import get_schedule_embed

class ScheduleAnimeSelect(discord.ui.View):
    def __init__(self, bot, schedule: dict, current_day: str):
        super().__init__(timeout=180)
        self.bot = bot
        self.schedule = schedule
        self.msg = None

        self.add_item(ScheduleDropdown(self, current_day))

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.msg:
            await self.msg.edit(view=self)

class ScheduleDropdown(discord.ui.Select):
    def __init__(self, parent: ScheduleAnimeSelect, default_day: str):
        self.parent = parent
        options = [
            discord.SelectOption(label=day, default=(day == default_day))
            for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        ]

        super().__init__(
            placeholder="Select a day...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="anime_schedule_day"
        )
    
    async def callback(self, itr: discord.Interaction):
        await itr.response.defer()

        selected_day = self.values[0]
        tz = pytz.timezone("Asia/Calcutta")
        current_time = datetime.now(tz)

        embed = get_schedule_embed(
            self.parent.schedule.get(selected_day, []),
            current_time
        )
        await itr.message.edit(embed=embed, view=self.parent)
  
class ConfirmUnfollowView(discord.ui.View):
    def __init__(self, bot, anime_title: str, user_id: int):
        super().__init__(timeout=30)
        self.bot = bot
        self.anime_title = anime_title
        self.user_id = user_id
        self.message = None

    async def on_timeout(self):
        self.disable_buttons()
        if self.message:
            await self.message.edit(content="⏰ Prompt timed out.", view=self)

    @discord.ui.button(label="Yes, unfollow", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, itr: discord.Interaction, btn: discord.ui.Button):
        await itr.response.defer()

        if itr.user.id != self.user_id:
            return await itr.followup.send("⚠️ This interaction isn't for you.", ephemeral=True)
        
        await self.bot.db.execute(
            "DELETE FROM anime_users WHERE anime_title = %s AND user_id = %s",
            self.anime_title, self.user_id
        )

        self.disable_buttons()
        embed = discord.Embed(
            title="Unfollowed Anime ✅",
            description=f"You have successfully unfollowed **{self.anime_title}**.",
            color=discord.Color.green()
        )
        await itr.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, itr: discord.Interaction, btn: discord.ui.Button):
        await itr.response.defer()

        if itr.user.id != self.user_id:
            return await itr.followup.send("⚠️ This interaction isn't for you.", ephemeral=True)

        self.disable_buttons()
        await itr.edit_original_response(content="❌ Unfollow cancelled.", view=self)

    def disable_buttons(self):
        for item in self.children:
            item.disabled = True

