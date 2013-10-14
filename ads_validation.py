def is_number(s):
	""" Returns True if string is castable to float """
	try:
		float(s)
		return True
	except ValueError:
		return False

def is_alphanumeric(s):
	""" Returns True if s is alpha numberic """
	from string import ascii_letters, digits
	return all(c in ascii_letters + '-_' + digits for c in 'testthis1-_string2233')
