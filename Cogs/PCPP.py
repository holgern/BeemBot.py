import requests
from   pyquery import PyQuery as pq

def find_last_between( source, start_sep, end_sep ):
	result=[]
	tmp=source.split(start_sep)
	for par in tmp:
		if end_sep in par:
			result.append(par.split(end_sep)[0])
	if len(result) == 0:
		return None
	else:
		return result[len(result)-1] # Return last item

def normalStyle(types, names, escape = False):
	padTo = 0
	for t in types:
		# Find out which has the longest
		tempLen = len(t)
		if tempLen > padTo:
			padTo = tempLen
	if escape:
		partdown = '\`\`\`\n'
	else:
		partdown = '```\n'
	for i in range(0, len(types)):
		partdown += types[i].rjust(padTo, ' ') + ' : ' + names[i] + '\n'
	if escape:
		partdown += '\`\`\`'
	else:
		partdown += '```'
	return partdown

def mdStyle(types, names, escape = False):
	padTo = 0
	for t in types:
		# Find out which has the longest
		ty = "<" + t.replace(' ', '-') + ":"
		tempLen = len(ty)
		if tempLen > padTo:
			padTo = tempLen
	if escape:
		partdown = '\`\`\`md\n'
	else:
		partdown = '```md\n'
	for i in range(0, len(types)):
		t = "<" + types[i].replace(' ', '-') + ":"
		partdown += t.ljust(padTo, ' ') + " " + names[i] + '>\n'
	if escape:
		partdown += '\`\`\`'
	else:
		partdown += '```'
	return partdown

def mdBlockStyle(types, names, escape = False):
	padTo = 0
	for t in types:
		# Find out which has the longest
		ty = "[" + t
		tempLen = len(ty)
		if tempLen > padTo:
			padTo = tempLen
	if escape:
		partdown = '\`\`\`md\n'
	else:
		partdown = '```md\n'
	for i in range(0, len(types)):
		ty = "[" + types[i]
		t = "| " + ty.rjust(padTo, ' ') + "]["
		partdown += t.rjust(padTo, ' ') + names[i] + ']\n'
	if escape:
		partdown += '\`\`\`'
	else:
		partdown += '```'
	return partdown

def boldStyle(types, names, escape = False):
	partdown = ''
	for i in range(0, len(types)):
		if escape:
			partdown += "\*\*" + types[i] + ":\*\* " + names[i] + '\n'
		else:
			partdown += "**" + types[i] + ":** " + names[i] + '\n'
	partdown = partdown[:-1]
	return partdown

def boldItalicStyle(types, names, escape = False):
	partdown = ''
	for i in range(0, len(types)):
		if escape:
			partdown += "\*\*\*" + types[i] + ":\*\*\* \*" + names[i] + '\*\n'
		else:
			partdown += "***" + types[i] + ":*** *" + names[i] + '*\n'
	partdown = partdown[:-1]
	return partdown
		
def getMarkdown( url, style = None, escape = False):
	# Ensure we're using a list
	if '/b/' in url.lower():
		# We have a build
		try:
			response = requests.get(url)
		except Exception:
			return None
		r = response.text
		newLink = find_last_between(r, 'href=\"list/', '">View')
		print("NewLink: {}".format(newLink))
		if newLink == None:
			return None
		url = "https://pcpartpicker.com/list/" + str(newLink)
		print(url)
		
	# url = url.replace('/b/', '/list/')
	if not style:
		style = 'normal'
	try:
		response = requests.get(url)
	except Exception:
		return None
	dom = pq(response.text)
	
	# Experimental crap because developing while not at home
	table = dom('table.manual-zebra').children('tbody').children()
	names = []
	types = []
	for i in range(0, len(table)):
		child = table.eq(i)
		try:
			children = child.children()
		except AttributeError:
			continue
		if len(children) < 3:
			continue
		# We should have enough
		type = children[0].text_content().strip().replace('\r', '').replace('\n', ' ').replace('\t', ' ')
		name = children[2].text_content().strip().replace('\r', '').replace('\n', ' ').replace('\t', ' ')
		if not len(name):
			# Didn't get a name
			continue
		# We got a name - awesome
		if name.lower().startswith('note:'):
			# Not a part
			continue
		names.append(name)
		if not len(type):
			if not len(types):
				# Nothing yet - this is weird
				types.append('-')
			else:
				types.append(types[len(types)-1])
		else:
			types.append(type)
	
	if not len(types):
		return None
	if not len(types) == len(names):
		# Only way this would happen that I've seen so far, is with custom entries
		return None
	partout = ''
	if style.lower() == 'md':
		partout = mdStyle(types, names, escape)
	elif style.lower() == 'mdblock':
		partout = mdBlockStyle(types, names, escape)
	elif style.lower() == 'bold':
		partout = boldStyle(types, names, escape)
	elif style.lower() == 'bolditalic':
		partout = boldItalicStyle(types, names, escape)
	else:
		partout = normalStyle(types, names, escape)
	return partout
