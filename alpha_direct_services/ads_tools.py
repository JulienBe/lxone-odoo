from datetime import datetime

ads_date_format = '%Y%m%d'

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
	d = str(d)
	if len(d) > 19:
		return datetime.strptime(d, '%Y-%m-%d %H:%M:%S.%f')
	elif len(d) > 8:
		return datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
	else:
		return datetime.strptime(d, '%Y%m%d')
