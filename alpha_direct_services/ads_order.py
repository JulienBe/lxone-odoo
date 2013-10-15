#!/usr/bin/python

from ads_data import ads_data

class ads_order(ads_data):

	data_type = 'ORDER'

	def set_shipping(self, civility=None, firstname=None, name=None, corp_name=None, adr1=None, \
		adr2=None, adr3=None, adr4=None, country=None, zip=None, city=None, phone=None, email=None):
		self.insert_data('order.header.customer.shipping_address', locals())

	def process(self, pool, cr):
		""" 
		Called when an XML file is downloaded from the ADS server. Override this method to
		do something with self.data in OpenERP.
		@param pool: OpenERP object pool 
		@param cr: OpenERP database cursor
		@returns True if successful. If True, the xml file on the FTP server will be deleted.
		"""
		print 'TODO: do something with self.data ;)'
		return False
