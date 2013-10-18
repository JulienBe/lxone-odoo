#!/usr/bin/python
from ads_data import ads_data
from datetime import datetime
from ads_tools import convert_date

class ads_sales_order(ads_data):

	data_type = 'ORDER'
	xml_root = 'orders'

	def extract(self, picking):
		"""
		Takes a stock.picking.out browse_record and extracts the
		appropriate data into self.data

		@param picking: browse_record(stock.picking.in)
		"""
		return self

	def process(self, pool, cr):
		"""
		Called when an XML file is downloaded from the ADS server. Override this method to
		do something with self.data in OpenERP.
		@param pool: OpenERP object pool
		@param cr: OpenERP database cursor
		@returns True if successful. If True, the xml file on the FTP server will be deleted.
		"""
		return False
