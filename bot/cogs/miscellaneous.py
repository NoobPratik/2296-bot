import json
from random import choice

import discord
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

class Fun(commands.Cog, name='miscellaneous', description='**Just some commands to have fun**'):
    def __init__(self, bot):
        self.minecraft_recipes = {}
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.collect_recipes()

    @app_commands.command(name='avatar', description="View a user's profile picture in full resolution.")
    async def avatar(self, itr: discord.Interaction, member: discord.Member = None):
        if member is None:
            member = itr.user

        av_embed2 = discord.Embed(title='Avatar', colour=0x7F00FF)
        av_embed2.set_author(name=member.name, icon_url=member.avatar.url)
        av_embed2.set_image(url=member.avatar.url)
        await itr.response.send_message(embed=av_embed2)

    @app_commands.command(name='8ball', description='	Ask the magic 8-ball a question and get a yes/no answer.')
    async def _8ball(self, itr: discord.Interaction, question: str):
        options = ['Hmm', 'Yes', 'No', 'Maybe', 'NOPE', 'YES', 'Shut up idot']
        random = choice(options)
        e = discord.Embed(title=question, description=random, colour=0x7F00FF)
        e.set_footer(icon_url=itr.user.avatar.url, text=f'Asked By {itr.user.name}')
        await itr.response.send_message(embed=e)

    async def recipe_autocomplete(self, itr: discord.Interaction, current: str):
        choices = []
        for match in [item for item in self.minecraft_recipes if item.lower().startswith(current)][:25]:
            choices.append(Choice(name=match, value=match))
        return choices

    @app_commands.command(name='minecraft-recipe', description="Look up crafting recipes for Minecraft items.")
    @app_commands.autocomplete(recipe=recipe_autocomplete)
    async def minecraft(self, itr: discord.Interaction, recipe: str):
        embed = discord.Embed(colour=self.bot.color)
        data = self.minecraft_recipes[recipe]
        embed.title = recipe
        embed.description = data['description']
        embed.set_image(url=f'https://www.minecraftcrafting.info/{data["image"]}')
        embed.set_footer(text=f'Ingredients: {data["ingredients"]}')
        await itr.response.send_message(embed=embed)

    def collect_recipes(self):
        r = requests.get('https://www.minecraftcrafting.info/')
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.find_all('tr')

        for row in rows[3:]:

            tds = row.find_all('td')
            if not len(tds) >= 4:
                continue
            
            name = tds[0].text.strip()
            ingredients = tds[1].text.strip()

            image_element = tds[2].find('img')
            if not image_element:
                continue
            
            image_src = image_element['src'].strip()
            description = tds[3].text.strip()
            self.minecraft_recipes[name] = {
                'ingredients': ingredients, 
                'image': image_src,
                'description': description
            }

async def setup(bot):
    await bot.add_cog(Fun(bot))