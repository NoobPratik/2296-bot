from discord import app_commands, Embed, Interaction, ui, SelectOption
from discord.ext import commands
from typing import Optional, Union


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_all_subcommands(self, cmd: Union[app_commands.Command, app_commands.Group]):
        if isinstance(cmd, app_commands.Command):
            return [cmd]
        commands = []
        for sub in cmd.commands:
            commands.extend(self.get_all_subcommands(sub))
        return commands

    @app_commands.command(name="help", description="View help for all commands or a specific command.")
    @app_commands.describe(command="Name of a specific command to get detailed help")
    async def help(self, interaction: Interaction, command: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)

        if command:
            all_commands = [cmd for group in self.bot.tree.get_commands() for cmd in self.get_all_subcommands(group)]
            target = next((cmd for cmd in all_commands if cmd.name == command), None)
            if not target:
                return await interaction.followup.send("Command not found.", ephemeral=True)

            embed = Embed(
                title=f"/{target.qualified_name}",
                description=target.description or "No description.",
                color=0x5865F2
            )
            if target.parameters:
                usage = " ".join([f"<{p.name}>" for p in target.parameters])
                embed.add_field(name="Usage", value=f"/{target.qualified_name} {usage}")
            return await interaction.followup.send(embed=embed, ephemeral=True)

        grouped = {}
        for group in self.bot.tree.get_commands():
            if isinstance(group, app_commands.Group):
                for sub in self.get_all_subcommands(group):
                    grouped.setdefault(group.name, []).append(sub)
            else:
                grouped.setdefault("Miscellaneous", []).append(group)

        cog_descriptions = {
            "anime": "Search, follow, and explore anime info and schedules.",
            "admin": "Server moderation and bot configuration utilities.",
            "music": "Tools to configure music features in your server.",
            "games": "Play interactive games like RPS, Memory, and Tic Tac Toe.",
            "valorant": "View ranks, match history, and performance insights.",
            "miscellaneous": "Fun, utility, and general-purpose commands.",
            "help": "View slash command help and usage tips."
        }

        class CogSelect(ui.Select):
            def __init__(self, embeds_by_cog):
                options = [
                    SelectOption(label=cog.capitalize(), description=cog_descriptions.get(cog.lower(), ""), value=cog)
                    for cog in embeds_by_cog
                ]
                super().__init__(placeholder="Select a command category...", options=options, min_values=1, max_values=1)
                self.embeds_by_cog = embeds_by_cog

            async def callback(self, interaction: Interaction):
                selected_embed = self.embeds_by_cog[self.values[0]]
                await interaction.response.edit_message(embed=selected_embed, view=self.view)

        embeds_by_cog = {}
        for cog_name, cmds in grouped.items():
            pretty_name = cog_name.capitalize()
            embed = Embed(
                title=f"{pretty_name} Commands",
                description=cog_descriptions.get(cog_name, "Commands available in this category."),
                color=self.bot.color
            )
            for cmd in cmds:
                embed.add_field(name=f"/{cmd.qualified_name}", value=cmd.description or "No description.", inline=False)
            embeds_by_cog[cog_name] = embed

        view = ui.View()
        view.add_item(CogSelect(embeds_by_cog))
        default_embed = next(iter(embeds_by_cog.values()))
        await interaction.followup.send(embed=default_embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
