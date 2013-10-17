#!/usr/bin/python

import sys
import StringIO
from lxml import etree
import re
from datetime import datetime

from picklingtools.xmldumper import *
from picklingtools import xml2dict
from auto_vivification import AutoVivification

class ads_data(object):
	"""
	Interface between OpenERP dict data and ADS XML data. Designed to be inherited
	so you can implement your own data input and output functions that build
	the self.data AutoVivification object (See ads_order class for an example).
	Don't forget to set the data_type and xml_root variables to define the file name 
	prefix and xml file root element name.

	After building the self.data dict, parse this object to the upload_data function
	of the ads_conn object. It will call the generate_xml to convert the self.data dict
	into an xml file, then upload it to the server.

	Alternatively, convert an ADS xml file into an ads_data dict by passing the XML 
	into the constructor.
	"""
	
	def __init__(self, xml=None):
		super(ads_data, self).__init__()
		self.data = AutoVivification()
		
		if xml:
			assert isinstance(xml, (str, unicode)), 'XML must be string or unicode'
			self.data = xml2dict.ConvertFromXML(xml)
			self.data = AutoVivification.dict_to_auto_vivification(self.data)
	
	data_type = None
	xml_root = None

	def insert_data(self, insert_target, params):
		""" 
		Insert keys and values from params into self.data at insert_target.
		Calling this method twice on the same key will convert the key from a dict
		to a list of dicts. In this way it can handle multiple xml nodes with
		the same name.
		 
		@param dict params: keys and values to insert into self.data
		@param str insert_target: dot separated values for insert target. For example
								  'order.customer' inserts to self.data['order']['customer']
		"""
		# save reference to the target key inside the nested dictionary self.data
		target = self.data
		for target_key in insert_target.split('.'):
			parent = target
			target = target[target_key]
		
		# have we already saved data to this key? If yes, convert it to a list
		# of dictionaries and add a second one 
		if isinstance(target, AutoVivification) and len(target) != 0:
			autoviv = True
			parent[target_key] = [target]
			target = parent[target_key]
		else:
			autoviv = False
		
		if not autoviv:
			# add data to the empty dict like normal
			for param_name in params:
				param_value = params[param_name]
	
				if not param_name == 'self':
					target[param_name] = param_value
		else:
			# create new dict to be added to the list of dicts
			val = AutoVivification()
			for param_name in params:
				param_value = params[param_name]
				
				if not param_name == 'self':
					val[param_name] = param_value
					
			target.append(val)
				
	def name(self):
		""" Generate a name for the uploaded xml file """
		assert self.data_type, 'The self.data_type variable must be set in your inheriting class'
		return '%s-%s.xml' % (self.data_type, datetime.today().strftime('%Y%m%d-%H%M%S'))

	def generate_xml(self):
		""" Returns a StringIO containing an XML representation of self.data nested dict """
		assert self.xml_root != None, 'The self.xml_root variable must be set in your inheriting class'
		output = StringIO.StringIO()
		xd = XMLDumper(output, XML_DUMP_PRETTY | XML_STRICT_HDR)
		xd.XMLDumpKeyValue(self.xml_root, self.data.to_dict())
		output.seek(0)
		return output

	def process(self, pool, cr):
		""" 
		Called when an XML file is downloaded from the ADS server. Override this method to
		do something with self.data in OpenERP.
		@param pool: OpenERP object pool 
		@param cr: OpenERP database cursor
		@returns True if successful. If True, the xml file on the FTP server will be deleted.
		"""
		raise NotImplementedError('This method must be implemented in a subclass')
