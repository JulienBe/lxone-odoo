from copy import copy
from ads_data import ads_data

class ads_stock_move(ads_data):

	data_type = 'MVTS'
	xml_root = 'adsxml'

	def process(self, pool, cr):
		"""
		Executes the reception wizard for the appropriate IN
		@param pool: OpenERP object pool
		@param cr: OpenERP database cursor
		@returns True if successful. If True, the xml file on the FTP server will be deleted.
		"""
		return False
