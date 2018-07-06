import asyncio
import discord
import string
import os
import re
from prettytable import PrettyTable
from   datetime import datetime
from   discord.ext import commands
from   Cogs import Settings
from   Cogs import Message
from   Cogs import Nullify
from   Cogs import PCPP
from beem import Steem
from beem.account import Account
from beem.comment import Comment
from beem.nodelist import NodeList

def setup(bot):
    # Add the bot and deps
    settings = bot.get_cog("Settings")
    bot.add_cog(Beem(bot, settings))


class Beem:

    def __init__(self, bot, settings):
        self.bot = bot
        self.settings = settings
        self.stm = Steem()

    def _is_admin(self, member, channel, guild):
        # Check for admin/bot-admin
        isAdmin = member.permissions_in(channel).administrator
        if not isAdmin:
            checkAdmin = self.settings.getServerStat(guild, "AdminArray")
            for role in member.roles:
                for aRole in checkAdmin:
                    # Get the role that corresponds to the id
                    if str(aRole['ID']) == str(role.id):
                        isAdmin = True
        return isAdmin

    @commands.command(pass_context=True)
    async def account(self, ctx, *, account : str = None):
        """Retuns information about an account"""
        if account is None:
            regAccount = self.settings.getUserStat(ctx.message.author, ctx.message.guild, "SteemAccount")
            if regAccount is not None and regAccount != "":
                account = regAccount
            else:
                account = ctx.message.author
                account = str(account).split('#')[0]
        a = Account(account, steem_instance=self.stm)
        response = a.print_info(return_str=True)
        await ctx.channel.send("```" + response + "```")

    @commands.command(pass_context=True)
    async def register(self, ctx, *, account : str = None):
        """Register your steemit name"""
        if account is None:
            await ctx.channel.send("I do nothing!")
            return
        try:
            Account(account, steem_instance=self.stm)
        except:
            await ctx.channel.send("Could not register %s!" % account)
            return
        self.settings.setUserStat(ctx.message.author, ctx.message.guild, "SteemAccount", account)
        await ctx.channel.send("Registered!")

    @commands.command(pass_context=True)
    async def updatenodes(self, ctx):
        """Retuns information about the current node"""
        t = PrettyTable(["node", "Version", "score"])
        t.align = "l"
        nodelist = NodeList()
        nodelist.update_nodes(steem_instance=self.stm)
        nodes = nodelist.get_nodes()
        sorted_nodes = sorted(nodelist, key=lambda node: node["score"], reverse=True)
        for node in sorted_nodes:
            if node["url"] in nodes:
                score = float("{0:.1f}".format(node["score"]))
                t.add_row([node["url"], node["version"], score])
        response = t.get_string()
        self.stm.set_default_nodes(nodes)

        await ctx.channel.send("```" + response + "```")

    @commands.command(pass_context=True)
    async def pricehistory(self, ctx):
        """Retuns information about the current steem price"""

        feed_history = self.stm.get_feed_history()
        current_base = Amount(feed_history['current_median_history']["base"], steem_instance=self.stm)
        current_quote = Amount(feed_history['current_median_history']["quote"], steem_instance=self.stm)
        price_history = feed_history["price_history"]
        price = []
        for h in price_history:
            base = Amount(h["base"], steem_instance=self.stm)
            quote = Amount(h["quote"], steem_instance=self.stm)
            price.append(base.amount / quote.amount)
        # charset = u'ascii'
        charset = u'utf8'
        chart = AsciiChart(height=10, width=30, offset=4, placeholder='{:6.2f} $', charset=charset)
        response = "Price history for STEEM (median price %4.2f $)\n" % (float(current_base) / float(current_quote))
    
        chart.adapt_on_series(price)
        chart.new_chart()
        chart.add_axis()
        chart._draw_h_line(chart._map_y(float(current_base) / float(current_quote)), 1, int(chart.n / chart.skip), line=chart.char_set["curve_hl_dot"])
        chart.add_curve(price)
        response += str(chart)
        await ctx.channel.send("```" + response + "```")

    @commands.command(pass_context=True)
    async def curation(self, ctx, *, authorperm : str):

        show_all_voter = False

        all_posts = False
        t = PrettyTable(["Voter", "Voting time", "Vote", "Early vote loss", "Curation", "Performance"])
        t.align = "l"
        index = 0

        index += 1
        comment = Comment(authorperm, steem_instance=self.stm)
        payout = None
        curation_rewards_SBD = comment.get_curation_rewards(pending_payout_SBD=True, pending_payout_value=payout)
        curation_rewards_SP = comment.get_curation_rewards(pending_payout_SBD=False, pending_payout_value=payout)
        rows = []
        sum_curation = [0, 0, 0, 0]
        max_curation = [0, 0, 0, 0, 0, 0]
        highest_vote = [0, 0, 0, 0, 0, 0]
        for vote in comment["active_votes"]:
            vote_SBD = self.stm.rshares_to_sbd(int(vote["rshares"]))
            curation_SBD = curation_rewards_SBD["active_votes"][vote["voter"]]
            curation_SP = curation_rewards_SP["active_votes"][vote["voter"]]
            if vote_SBD > 0:
                penalty = ((comment.get_curation_penalty(vote_time=vote["time"])) * vote_SBD)
                performance = (float(curation_SBD) / vote_SBD * 100)
            else:
                performance = 0
                penalty = 0
            vote_befor_min = (((vote["time"]) - comment["created"]).total_seconds() / 60)
            sum_curation[0] += vote_SBD
            sum_curation[1] += penalty
            sum_curation[2] += float(curation_SP)
            sum_curation[3] += float(curation_SBD)
            row = [vote["voter"],
                   vote_befor_min,
                   vote_SBD,
                   penalty,
                   float(curation_SP),
                   performance]
            if row[-1] > max_curation[-1]:
                max_curation = row
            if row[2] > highest_vote[2]:
                highest_vote = row
            rows.append(row)
        sortedList = sorted(rows, key=lambda row: (row[1]), reverse=False)
        new_row = []
        new_row2 = []
        voter = []
        voter2 = []

        voter = [""]
        voter2 = [""]
        for row in sortedList:
            if show_all_voter:
                if not all_posts:
                    voter = [row[0]]
                if all_posts:
                    new_row[0] = "%d. %s" % (index, comment.author)
                t.add_row(new_row + voter + ["%.1f min" % row[1],
                                             "%.3f SBD" % float(row[2]),
                                             "%.3f SBD" % float(row[3]),
                                             "%.3f SP" % (row[4]),
                                             "%.1f %%" % (row[5])])
                
                new_row = new_row2
        t.add_row(new_row2 + voter2 + ["", "", "", "", ""])
        if sum_curation[0] > 0:
            curation_sum_percentage = sum_curation[3] / sum_curation[0] * 100
        else:
            curation_sum_percentage = 0
        sum_line = new_row2 + voter2
        sum_line[-1] = "High. vote"

        t.add_row(sum_line + ["%.1f min" % highest_vote[1],
                              "%.3f SBD" % float(highest_vote[2]),
                              "%.3f SBD" % float(highest_vote[3]),
                              "%.3f SP" % (highest_vote[4]),
                              "%.1f %%" % (highest_vote[5])])
        sum_line[-1] = "High. Cur."
        t.add_row(sum_line + ["%.1f min" % max_curation[1],
                              "%.3f SBD" % float(max_curation[2]),
                              "%.3f SBD" % float(max_curation[3]),
                              "%.3f SP" % (max_curation[4]),
                              "%.1f %%" % (max_curation[5])])
        sum_line[-1] = "Sum"
        t.add_row(sum_line + ["-",
                              "%.3f SBD" % (sum_curation[0]),
                              "%.3f SBD" % (sum_curation[1]),
                              "%.3f SP" % (sum_curation[2]),
                              "%.2f %%" % curation_sum_percentage])
        response = "curation for %s\n" % (authorperm)
        response += t.get_string()
        await ctx.channel.send("```" + response + "```")

