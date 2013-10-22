from copy import copy

from ads_data import ads_data
from ads_tools import convert_date

class ads_sales_order(ads_data):

	data_type = 'CMDE'
	xml_root = 'orders'

	def extract(self, picking):
		"""
		Takes a stock.picking.out browse_record and extracts the
		appropriate data into self.data

		@param picking: browse_record(stock.picking.in)
		"""
		
		
		
		return self
