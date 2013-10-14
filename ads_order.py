#!/usr/bin/python

from ads_data import ads_data

class ads_order(ads_data):

	type = 'ORDER'

	def set_shipping(self, civility=None, firstname=None, name=None, corp_name=None, adr1=None, \
		adr2=None, adr3=None, adr4=None, country=None, zip=None, city=None, phone=None, email=None):
		self.insert_data('order.header.customer.shipping_address', locals())

