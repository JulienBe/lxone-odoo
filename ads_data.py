#!/usr/bin/python

import sys
import StringIO
from lxml import etree
import re

from picklingtools.xmldumper import *
from auto_vivification import AutoVivification
import ads_validation

class ads_data(object):
	"""
	Interface between OpenERP dict data and ADS XML data. Designed to be inherited
	so you can implement your own data input and output functions that build
	the self.data AutoVivification object (See ads_order class for an example).

	After building the self.data dict, you can call generate_xml to parse dict into 
	XML for uploading to the ADS server, or hand this object to the upload_data 
	function of ads_conn.

	Alternatively, parse an XML file from ADS into the self.data object by calling parse_xml.
	"""
	
	def __init__(self, xml=None):
		super(ads_data, self).__init__()
		if xml:
			assert isinstance(xml, (str, unicode)), 'XML must be string or unicode'
			print 'TODO: parse XML'

	data = AutoVivification()

	def insert_data(self, insert_target, params):
		""" 
		Insert keys and values from params into self.data at insert_target 
		@param params dict: keys and values to insert into self.data
		@param insert_target str: dot separated values for insert target. For example
								  'order.customer' inserts to self.data['order']['customer']
		"""
		target = self.data
		for target_key in insert_target.split('.'):
			target = target[target_key]

		for param_name in params:
			param_value = params[param_name]

			if not param_name == 'self':
				target[param_name] = param_value

	def generate_xml(self):
		""" Returns string containing XML representation of self.data nested dict """
		output = StringIO.StringIO()
		xd = XMLDumper(output)
		xd.XMLDumpKeyValue('first', self.data.to_dict())
		xml = output.getvalue()
		output.close()
		return xml
