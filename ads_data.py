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

	data = AutoVivification()

	def insert_data(self, insert_target, params):
		"""  """
		target = self.data
		for target_key in insert_target.split('.'):
			target = target[target_key]

		for param_name in params:
			param_value = params[param_name]

			if not param_name == 'self':
				target[param_name] = param_value

	def _parse_xml(self, xml):
		""" Convert XML data from ADS to dict format """
		print 'TODO: parse_xml'
		return {}
	
	def generate_xml(self):
		""" Returns string containing XML compliant with a format that ADS is expecting """

		log = StringIO.StringIO()
		xd = XMLDumper(log)

		xd.XMLDumpKeyValue('first', self.data)
		log_val = log.getvalue()

		print log_val
		log.close()

		return str(self.data)
