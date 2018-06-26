import asyncio
import discord
import string
import os
import re
from   datetime import datetime
from   discord.ext import commands
from   Cogs import Settings
from   Cogs import Message
from   Cogs import Nullify
from   Cogs import PCPP
from beem import Steem
from beem.account import Account

def setup(bot):
	# Add the bot and deps
	settings = bot.get_cog("Settings")
	bot.add_cog(Beem(bot, settings))


class Beem:

    def __init__(self, bot, settings):
        self.bot = bot
        self.settings = settings
        self.stm = Steem()
       
    @commands.command(pass_context=True)
    async def account(self, ctx, *, account : str = None):
        """Retuns information about an account"""
        if account is None:
            account = ctx.message.author
            account = str(account).split('#')[0]
        a = Account(account, steem_instance=self.stm)
        response = a.print_info(return_str=True)
        await ctx.channel.send("```" + response + "```")
