import asyncio
import discord
import random
from   discord.ext import commands
from   Cogs import Settings
from   Cogs import DisplayName
from   Cogs import Nullify

def setup(bot):
	# Add the bot and deps
	settings = bot.get_cog("Settings")
	bot.add_cog(UserRole(bot, settings))

class UserRole:
	
	def __init__(self, bot, settings):
		self.bot = bot
		self.settings = settings
		self.loop_list = []
		
	def _is_submodule(self, parent, child):
		return parent == child or child.startswith(parent + ".")
		
	@asyncio.coroutine
	async def on_unloaded_extension(self, ext):
		# Called to shut things down
		if not self._is_submodule(ext.__name__, self.__module__):
			return
		for task in self.loop_list:
			task.cancel()

	@asyncio.coroutine
	async def on_loaded_extension(self, ext):
		# See if we were loaded
		if not self._is_submodule(ext.__name__, self.__module__):
			return
		# Add a loop to remove expired user blocks in the UserRoleBlock list
		self.loop_list.append(self.bot.loop.create_task(self.block_check_list()))
		
	async def block_check_list(self):
		while not self.bot.is_closed():
			# Iterate through the ids in the UserRoleBlock list and 
			# remove any for members who aren't here
			for guild in self.bot.guilds:
				block_list = self.settings.getServerStat(guild, "UserRoleBlock")
				rem_list = [ x for x in block_list if not guild.get_member(x) ]
				if len(rem_list):
					block_list = [ x for x in block_list if x not in rem_list ]
					self.settings.setServerStat(guild, "UserRoleBlock", block_list)
				# Check once per hour
				await asyncio.sleep(3600)
	
	@commands.command(pass_context=True)
	async def urblock(self, ctx, *, member = None):
		"""Blocks a user from using the UserRole system and removes applicable roles (bot-admin only)."""
		isAdmin = ctx.author.permissions_in(ctx.channel).administrator
		if not isAdmin:
			checkAdmin = self.settings.getServerStat(ctx.guild, "AdminArray")
			for role in ctx.author.roles:
				for aRole in checkAdmin:
					# Get the role that corresponds to the id
					if str(aRole['ID']) == str(role.id):
						isAdmin = True
						break
		# Only allow bot-admins to change server stats
		if not isAdmin:
			await ctx.send('You do not have sufficient privileges to access this command.')
			return
		# Get the target user
		mem = DisplayName.memberForName(member, ctx.guild)
		if not mem:
			await ctx.send("I couldn't find `{}`.".format(member.replace("`", "\\`")))
			return
		# Check if we're trying to block a bot-admin
		isAdmin = mem.permissions_in(ctx.channel).administrator
		if not isAdmin:
			checkAdmin = self.settings.getServerStat(ctx.guild, "AdminArray")
			for role in mem.roles:
				for aRole in checkAdmin:
					# Get the role that corresponds to the id
					if str(aRole['ID']) == str(role.id):
						isAdmin = True
						break
		# Only allow bot-admins to change server stats
		if isAdmin:
			await ctx.send("You can't block other admins or bot-admins from the UserRole module.")
			return
		# At this point - we have someone to block - see if they're already blocked
		block_list = self.settings.getServerStat(ctx.guild, "UserRoleBlock")
		m = ""
		if mem.id in block_list:
			m += "`{}` is already blocked from the UserRole module.".format(DisplayName.name(mem).replace("`", "\\`"))
		else:
			block_list.append(mem.id)
			self.settings.setServerStat(ctx.guild, "UserRoleBlock", block_list)
			m += "`{}` now blocked from the UserRole module.".format(DisplayName.name(mem).replace("`", "\\`"))
		# Remove any roles
		# Get the array
		try:
			promoArray = self.settings.getServerStat(ctx.guild, "UserRoles")
		except Exception:
			promoArray = []
		if promoArray == None:
			promoArray = []
		# Populate the roles that need to be removed
		remRole = []
		for arole in promoArray:
			roleTest = DisplayName.roleForID(arole['ID'], ctx.guild)
			if not roleTest:
				# Not a real role - skip
				continue
			if roleTest in mem.roles:
				# We have it
				remRole.append(roleTest)
		if len(remRole):
			# Only remove if we have roles to remove
			self.settings.role.rem_roles(mem, remRole)
		m += "\n\n*{} {}* removed.".format(len(remRole), "role" if len(remRole) == 1 else "roles")
		await ctx.send(m)
	
	@commands.command(pass_context=True)
	async def urunblock(self, ctx, *, member = None):
		"""Unblocks a user from the UserRole system (bot-admin only)."""
		isAdmin = ctx.author.permissions_in(ctx.channel).administrator
		if not isAdmin:
			checkAdmin = self.settings.getServerStat(ctx.guild, "AdminArray")
			for role in ctx.author.roles:
				for aRole in checkAdmin:
					# Get the role that corresponds to the id
					if str(aRole['ID']) == str(role.id):
						isAdmin = True
						break
		# Only allow bot-admins to change server stats
		if not isAdmin:
			await ctx.send('You do not have sufficient privileges to access this command.')
			return
		# Get the target user
		mem = DisplayName.memberForName(member, ctx.guild)
		if not mem:
			await ctx.send("I couldn't find `{}`.".format(member.replace("`", "\\`")))
			return
		# At this point - we have someone to unblock - see if they're blocked
		block_list = self.settings.getServerStat(ctx.guild, "UserRoleBlock")
		if not mem.id in block_list:
			await ctx.send("`{}` is not blocked from the UserRole module.".format(DisplayName.name(mem).replace("`", "\\`")))
			return
		block_list.remove(mem.id)
		self.settings.setServerStat(ctx.guild, "UserRoleBlock", block_list)
		await ctx.send("`{}` has been unblocked from the UserRole module.".format(DisplayName.name(mem).replace("`", "\\`")))
	
	@commands.command(pass_context=True)
	async def isurblocked(self, ctx, *, member = None):
		"""Outputs whether or not the passed user is blocked from the UserRole module."""
		if member == None:
			member = "{}".format(ctx.author.mention)
		# Get the target user
		mem = DisplayName.memberForName(member, ctx.guild)
		if not mem:
			await ctx.send("I couldn't find `{}`.".format(member.replace("`", "\\`")))
			return
		block_list = self.settings.getServerStat(ctx.guild, "UserRoleBlock")
		name = "You are" if mem.id == ctx.author.id else "`"+DisplayName.name(mem).replace("`", "\\`") + "` is"
		if mem.id in block_list:
			await ctx.send(name + " blocked from the UserRole module.")
		else:
			await ctx.send(name + " not blocked from the UserRole module.")
	
	@commands.command(pass_context=True)
	async def adduserrole(self, ctx, *, role = None):
		"""Adds a new role to the user role system (admin only)."""
		
		author  = ctx.message.author
		server  = ctx.message.guild
		channel = ctx.message.channel

		usage = 'Usage: `{}adduserrole [role]`'.format(ctx.prefix)

		# Check if we're suppressing @here and @everyone mentions
		if self.settings.getServerStat(server, "SuppressMentions"):
			suppress = True
		else:
			suppress = False
		
		isAdmin = author.permissions_in(channel).administrator
		# Only allow admins to change server stats
		if not isAdmin:
			await channel.send('You do not have sufficient privileges to access this command.')
			return
		
		if role == None:
			await ctx.send(usage)
			return

		if type(role) is str:
			if role == "everyone":
				role = "@everyone"
			# It' a string - the hope continues
			roleCheck = DisplayName.roleForName(role, server)
			if not roleCheck:
				msg = "I couldn't find **{}**...".format(role)
				if suppress:
					msg = Nullify.clean(msg)
				await ctx.send(msg)
				return
			role = roleCheck

		# Now we see if we already have that role in our list
		try:
			promoArray = self.settings.getServerStat(server, "UserRoles")
		except Exception:
			promoArray = []
		if promoArray == None:
			promoArray = []

		for aRole in promoArray:
			# Get the role that corresponds to the id
			if str(aRole['ID']) == str(role.id):
				# We found it - throw an error message and return
				msg = '**{}** is already in the list.'.format(role.name)
				# Check for suppress
				if suppress:
					msg = Nullify.clean(msg)
				await channel.send(msg)
				return

		# If we made it this far - then we can add it
		promoArray.append({ 'ID' : role.id, 'Name' : role.name })
		self.settings.setServerStat(server, "UserRoles", promoArray)

		msg = '**{}** added to list.'.format(role.name)
		# Check for suppress
		if suppress:
			msg = Nullify.clean(msg)
		await channel.send(msg)
		return

	@adduserrole.error
	async def adduserrole_error(self, ctx, error):
		# do stuff
		msg = 'adduserrole Error: {}'.format(ctx)
		await error.channel.send(msg)

	@commands.command(pass_context=True)
	async def removeuserrole(self, ctx, *, role = None):
		"""Removes a role from the user role system (admin only)."""
		
		author  = ctx.message.author
		server  = ctx.message.guild
		channel = ctx.message.channel

		usage = 'Usage: `{}removeuserrole [role]`'.format(ctx.prefix)

		# Check if we're suppressing @here and @everyone mentions
		if self.settings.getServerStat(server, "SuppressMentions"):
			suppress = True
		else:
			suppress = False
		
		isAdmin = author.permissions_in(channel).administrator
		# Only allow admins to change server stats
		if not isAdmin:
			await channel.send('You do not have sufficient privileges to access this command.')
			return

		if role == None:
			await channel.send(usage)
			return

		if type(role) is str:
			if role == "everyone":
				role = "@everyone"
			# It' a string - the hope continues
			# Let's clear out by name first - then by role id
			try:
				promoArray = self.settings.getServerStat(server, "UserRoles")
			except Exception:
				promoArray = []
			if promoArray == None:
				promoArray = []

			for aRole in promoArray:
				# Get the role that corresponds to the name
				if aRole['Name'].lower() == role.lower():
					# We found it - let's remove it
					promoArray.remove(aRole)
					self.settings.setServerStat(server, "UserRoles", promoArray)
					msg = '**{}** removed successfully.'.format(aRole['Name'])
					# Check for suppress
					if suppress:
						msg = Nullify.clean(msg)
					await channel.send(msg)
					return
			# At this point - no name
			# Let's see if it's a role that's had a name change


			roleCheck = DisplayName.roleForName(role, server)
			if roleCheck:
				# We got a role
				# If we're here - then the role is an actual role
				try:
					promoArray = self.settings.getServerStat(server, "UserRoles")
				except Exception:
					promoArray = []
				if promoArray == None:
					promoArray = []

				for aRole in promoArray:
					# Get the role that corresponds to the id
					if str(aRole['ID']) == str(roleCheck.id):
						# We found it - let's remove it
						promoArray.remove(aRole)
						self.settings.setServerStat(server, "UserRoles", promoArray)
						msg = '**{}** removed successfully.'.format(aRole['Name'])
						# Check for suppress
						if suppress:
							msg = Nullify.clean(msg)
						await channel.send(msg)
						return
				
			# If we made it this far - then we didn't find it
			msg = '*{}* not found in list.'.format(roleCheck.name)
			# Check for suppress
			if suppress:
				msg = Nullify.clean(msg)
			await channel.send(msg)
			return

		# If we're here - then the role is an actual role - I think?
		try:
			promoArray = self.settings.getServerStat(server, "UserRoles")
		except Exception:
			promoArray = []
		if promoArray == None:
			promoArray = []

		for aRole in promoArray:
			# Get the role that corresponds to the id
			if str(arole['ID']) == str(role.id):
				# We found it - let's remove it
				promoArray.remove(aRole)
				self.settings.setServerStat(server, "UserRoles", promoArray)
				msg = '**{}** removed successfully.'.format(aRole['Name'])
				# Check for suppress
				if suppress:
					msg = Nullify.clean(msg)
				await channel.send(msg)
				return

		# If we made it this far - then we didn't find it
		msg = '*{}* not found in list.'.format(role.name)
		# Check for suppress
		if suppress:
			msg = Nullify.clean(msg)
		await channel.send(msg)

	@removeuserrole.error
	async def removeuserrole_error(self, ctx, error):
		# do stuff
		msg = 'removeuserrole Error: {}'.format(ctx)
		await error.channel.send(msg)

	@commands.command(pass_context=True)
	async def listuserroles(self, ctx):
		"""Lists all roles for the user role system."""
		
		server  = ctx.message.guild
		channel = ctx.message.channel

		# Check if we're suppressing @here and @everyone mentions
		if self.settings.getServerStat(server, "SuppressMentions"):
			suppress = True
		else:
			suppress = False
		
		# Get the array
		try:
			promoArray = self.settings.getServerStat(server, "UserRoles")
		except Exception:
			promoArray = []
		if promoArray == None:
			promoArray = []


		if not len(promoArray):
			msg = "There aren't any roles in the user role list yet.  Add some with the `{}adduserrole` command!".format(ctx.prefix)
			await ctx.channel.send(msg)
			return

		# Sort by XP first, then by name
		# promoSorted = sorted(promoArray, key=itemgetter('XP', 'Name'))
		promoSorted = sorted(promoArray, key=lambda x:x['Name'])
		
		roleText = "**__Current Roles:__**\n\n"
		for arole in promoSorted:
			# Get current role name based on id
			foundRole = False
			for role in server.roles:
				if str(role.id) == str(arole['ID']):
					# We found it
					foundRole = True
					roleText = '{}**{}**\n'.format(roleText, role.name)
			if not foundRole:
				roleText = '{}**{}** (removed from server)\n'.format(roleText, arole['Name'])

		# Check for suppress
		if suppress:
			roleText = Nullify.clean(roleText)

		await channel.send(roleText)

	@commands.command(pass_context=True)
	async def oneuserrole(self, ctx, *, yes_no = None):
		"""Turns on/off one user role at a time (bot-admin only; always on by default)."""

		# Check for admin status
		isAdmin = ctx.author.permissions_in(ctx.channel).administrator
		if not isAdmin:
			checkAdmin = self.settings.getServerStat(ctx.guild, "AdminArray")
			for role in ctx.author.roles:
				for aRole in checkAdmin:
					# Get the role that corresponds to the id
					if str(aRole['ID']) == str(role.id):
						isAdmin = True
		if not isAdmin:
			await ctx.send("You do not have permission to use this command.")
			return

		setting_name = "One user role at a time"
		setting_val  = "OnlyOneUserRole"

		current = self.settings.getServerStat(ctx.guild, setting_val)
		if yes_no == None:
			if current:
				msg = "{} currently *enabled.*".format(setting_name)
			else:
				msg = "{} currently *disabled.*".format(setting_name)
		elif yes_no.lower() in [ "yes", "on", "true", "enabled", "enable" ]:
			yes_no = True
			if current == True:
				msg = '{} remains *enabled*.'.format(setting_name)
			else:
				msg = '{} is now *enabled*.'.format(setting_name)
		elif yes_no.lower() in [ "no", "off", "false", "disabled", "disable" ]:
			yes_no = False
			if current == False:
				msg = '{} remains *disabled*.'.format(setting_name)
			else:
				msg = '{} is now *disabled*.'.format(setting_name)
		else:
			msg = "That's not a valid setting."
			yes_no = current
		if not yes_no == None and not yes_no == current:
			self.settings.setServerStat(ctx.guild, setting_val, yes_no)
		await ctx.send(msg)

	@commands.command(pass_context=True)
	async def clearroles(self, ctx):
		"""Removes all user roles from your roles."""
		block_list = self.settings.getServerStat(ctx.guild, "UserRoleBlock")
		if ctx.author.id in block_list:
			await ctx.send("You are currently blocked from using this command.")
			return
		# Get the array
		try:
			promoArray = self.settings.getServerStat(ctx.guild, "UserRoles")
		except Exception:
			promoArray = []
		if promoArray == None:
			promoArray = []
		
		remRole = []
		for arole in promoArray:
			roleTest = DisplayName.roleForID(arole['ID'], ctx.guild)
			if not roleTest:
				# Not a real role - skip
				continue
			if roleTest in ctx.author.roles:
				# We have it
				remRole.append(roleTest)

		if not len(remRole):
			await ctx.send("You have no roles from the user role list.")
			return		
		self.settings.role.rem_roles(ctx.author, remRole)
		if len(remRole) == 1:
			await ctx.send("1 user role removed from your roles.")
		else:
			await ctx.send("{} user roles removed from your roles.".format(len(remRole)))


	@commands.command(pass_context=True)
	async def remrole(self, ctx, *, role = None):
		"""Removes a role from the user role list from your roles."""
		block_list = self.settings.getServerStat(ctx.guild, "UserRoleBlock")
		if ctx.author.id in block_list:
			await ctx.send("You are currently blocked from using this command.")
			return

		if role == None:
			await ctx.send("Usage: `{}remrole [role name]`".format(ctx.prefix))
			return

		server  = ctx.message.guild
		channel = ctx.message.channel

		if self.settings.getServerStat(server, "OnlyOneUserRole"):
			await ctx.invoke(self.setrole, role=None)
			return

		# Check if we're suppressing @here and @everyone mentions
		if self.settings.getServerStat(server, "SuppressMentions"):
			suppress = True
		else:
			suppress = False
		
		# Get the array
		try:
			promoArray = self.settings.getServerStat(server, "UserRoles")
		except Exception:
			promoArray = []
		if promoArray == None:
			promoArray = []

		# Check if role is real
		roleCheck = DisplayName.roleForName(role, server)
		if not roleCheck:
			# No luck...
			msg = '*{}* not found in list.\n\nTo see a list of user roles - run `{}listuserroles`'.format(role, ctx.prefix)
			# Check for suppress
			if suppress:
				msg = Nullify.clean(msg)
			await channel.send(msg)
			return
		
		# Got a role - set it
		role = roleCheck

		remRole = []
		for arole in promoArray:
			roleTest = DisplayName.roleForID(arole['ID'], server)
			if not roleTest:
				# Not a real role - skip
				continue
			if str(arole['ID']) == str(role.id):
				# We found it!
				if roleTest in ctx.author.roles:
					# We have it
					remRole.append(roleTest)
				else:
					# We don't have it...
					await ctx.send("You don't currently have that role.")
					return
				break

		if not len(remRole):
			# We didn't find that role
			msg = '*{}* not found in list.\n\nTo see a list of user roles - run `{}listuserroles`'.format(role.name, ctx.prefix)
			# Check for suppress
			if suppress:
				msg = Nullify.clean(msg)
			await channel.send(msg)
			return

		if len(remRole):
			self.settings.role.rem_roles(ctx.author, remRole)

		msg = '*{}* has been removed from **{}!**'.format(DisplayName.name(ctx.message.author), role.name)
		if suppress:
			msg = Nullify.clean(msg)
		await channel.send(msg)
		

	@commands.command(pass_context=True)
	async def addrole(self, ctx, *, role = None):
		"""Adds a role from the user role list to your roles.  You can have multiples at a time."""
		block_list = self.settings.getServerStat(ctx.guild, "UserRoleBlock")
		if ctx.author.id in block_list:
			await ctx.send("You are currently blocked from using this command.")
			return
		
		if role == None:
			await ctx.send("Usage: `{}addrole [role name]`".format(ctx.prefix))
			return

		server  = ctx.message.guild
		channel = ctx.message.channel

		if self.settings.getServerStat(server, "OnlyOneUserRole"):
			await ctx.invoke(self.setrole, role=role)
			return

		# Check if we're suppressing @here and @everyone mentions
		if self.settings.getServerStat(server, "SuppressMentions"):
			suppress = True
		else:
			suppress = False
		
		# Get the array
		try:
			promoArray = self.settings.getServerStat(server, "UserRoles")
		except Exception:
			promoArray = []
		if promoArray == None:
			promoArray = []

		# Check if role is real
		roleCheck = DisplayName.roleForName(role, server)
		if not roleCheck:
			# No luck...
			msg = '*{}* not found in list.\n\nTo see a list of user roles - run `{}listuserroles`'.format(role, ctx.prefix)
			# Check for suppress
			if suppress:
				msg = Nullify.clean(msg)
			await channel.send(msg)
			return
		
		# Got a role - set it
		role = roleCheck

		addRole = []
		for arole in promoArray:
			roleTest = DisplayName.roleForID(arole['ID'], server)
			if not roleTest:
				# Not a real role - skip
				continue
			if str(arole['ID']) == str(role.id):
				# We found it!
				if roleTest in ctx.author.roles:
					# We already have it
					await ctx.send("You already have that role.")
					return
				addRole.append(roleTest)
				break

		if not len(addRole):
			# We didn't find that role
			msg = '*{}* not found in list.\n\nTo see a list of user roles - run `{}listuserroles`'.format(role.name, ctx.prefix)
			# Check for suppress
			if suppress:
				msg = Nullify.clean(msg)
			await channel.send(msg)
			return

		if len(addRole):
			self.settings.role.add_roles(ctx.author, addRole)

		msg = '*{}* has acquired **{}!**'.format(DisplayName.name(ctx.message.author), role.name)
		if suppress:
			msg = Nullify.clean(msg)
		await channel.send(msg)

	@commands.command(pass_context=True)
	async def setrole(self, ctx, *, role = None):
		"""Sets your role from the user role list.  You can only have one at a time."""
		block_list = self.settings.getServerStat(ctx.guild, "UserRoleBlock")
		if ctx.author.id in block_list:
			await ctx.send("You are currently blocked from using this command.")
			return
		
		server  = ctx.message.guild
		channel = ctx.message.channel

		if not self.settings.getServerStat(server, "OnlyOneUserRole"):
			await ctx.invoke(self.addrole, role=role)
			return

		# Check if we're suppressing @here and @everyone mentions
		if self.settings.getServerStat(server, "SuppressMentions"):
			suppress = True
		else:
			suppress = False
		
		# Get the array
		try:
			promoArray = self.settings.getServerStat(server, "UserRoles")
		except Exception:
			promoArray = []
		if promoArray == None:
			promoArray = []

		if role == None:
			# Remove us from all roles
			remRole = []
			for arole in promoArray:
				roleTest = DisplayName.roleForID(arole['ID'], server)
				if not roleTest:
					# Not a real role - skip
					continue
				if roleTest in ctx.message.author.roles:
					# We have this in our roles - remove it
					remRole.append(roleTest)
			if len(remRole):
				self.settings.role.rem_roles(ctx.author, remRole)
			# Give a quick status
			msg = '*{}* has been moved out of all roles in the list!'.format(DisplayName.name(ctx.message.author))
			if suppress:
				msg = Nullify.clean(msg)
			await channel.send(msg)
			return

		# Check if role is real
		roleCheck = DisplayName.roleForName(role, server)
		if not roleCheck:
			# No luck...
			msg = '*{}* not found in list.\n\nTo see a list of user roles - run `{}listuserroles`'.format(role, ctx.prefix)
			# Check for suppress
			if suppress:
				msg = Nullify.clean(msg)
			await channel.send(msg)
			return
		
		# Got a role - set it
		role = roleCheck

		addRole = []
		remRole = []
		for arole in promoArray:
			roleTest = DisplayName.roleForID(arole['ID'], server)
			if not roleTest:
				# Not a real role - skip
				continue
			if str(arole['ID']) == str(role.id):
				# We found it!
				addRole.append(roleTest)
			elif roleTest in ctx.message.author.roles:
				# Not our intended role and we have this in our roles - remove it
				remRole.append(roleTest)

		if not len(addRole):
			# We didn't find that role
			msg = '*{}* not found in list.\n\nTo see a list of user roles - run `{}listuserroles`'.format(role.name, ctx.prefix)
			# Check for suppress
			if suppress:
				msg = Nullify.clean(msg)
			await channel.send(msg)
			return

		if len(remRole) or len(addRole):
			self.settings.role.change_roles(ctx.author, add_roles=addRole, rem_roles=remRole)

		msg = '*{}* has been moved to **{}!**'.format(DisplayName.name(ctx.message.author), role.name)
		if suppress:
			msg = Nullify.clean(msg)
		await channel.send(msg)
