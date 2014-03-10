from datetime import datetime
from dateutil.parser import parse

lx_date_format = '%Y%m%d'
openerp_date_format = '%Y-%m-%d %H:%M:%S'

def convert_date(d):
	""" Convert a date from various formats to LX1 format """
	if not d:
		return None
	if len(d) == 10:
		return datetime.strptime(d, '%Y-%m-%d').strftime(lx_date_format)
	else:
		return datetime.strptime(d, '%Y-%m-%d %H:%M:%S').strftime(lx_date_format)

def parse_date(d):
	""" Gets a datetime object from various string date formats """
	return parse(d, dayfirst=True)

def get_config(pool, cr, config_name, value_type=str):
    """
    Get a configuration value from ir.values by config_name (For this model)
    @param pool: oe object pool
    @param str config_name: The name of the ir.values record to get
    @param object value_type: Used to cast the value to an appropriate return type.
    """
    values_obj = pool.get('ir.config_parameter')
    value_ids = values_obj.search(cr, 1, [('key','=',config_name)])
    if value_ids:
        value = values_obj.browse(cr, 1, value_ids[0]).value
        return value_type(value)
    else:
        return None
