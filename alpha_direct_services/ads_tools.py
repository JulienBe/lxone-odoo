from datetime import datetime

ads_date_format = '%Y%m%d'
openerp_date_format = '%Y-%m-%d %H:%M:%S'

def convert_date(d):
	""" Convert a date from various formats to ADS format """
	if not d:
		return None
	if len(d) == 10:
		return datetime.strptime(d, '%Y-%m-%d').strftime(ads_date_format)
	else:
		return datetime.strptime(d, '%Y-%m-%d %H:%M:%S').strftime(ads_date_format)

def parse_date(d):
	""" Gets a datetime object from various string date formats """
	if not d:
		return None
	d = str(d)
	if len(d) > 19:
		return datetime.strptime(d, '%Y-%m-%d %H:%M:%S.%f')
	elif len(d) > 8:
		return datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
	else:
		return datetime.strptime(d, '%Y%m%d')
