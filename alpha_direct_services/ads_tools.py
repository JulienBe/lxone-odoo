from datetime import datetime

ads_date_format = '%Y%m%d'

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

def convert_date(d):
	if not d:
		return None
	if len(d) == 10:
		return datetime.strptime(d, '%Y-%m-%d').strftime(ads_date_format)
	else:
		return datetime.strptime(d, '%Y-%m-%d %H:%M:%S').strftime(ads_date_format)

def parse_date(d):
	if not d:
		return None
	if len(d) > 19:
		return datetime.strptime(d, '%Y-%m-%d %H:%M:%S.%f')
	elif len(d) > 8:
		return datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
	else:
		return datetime.strptime(d, '%Y%m%d')
