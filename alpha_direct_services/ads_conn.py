#!/usr/bin/python

from openerp.osv import osv, fields

from ftplib import FTP
import StringIO

from ads_data import ads_data
from ads_purchase_order import ads_purchase_order
from ads_sales_order import ads_sales_order
from ads_return import ads_return

class ads_conn(osv.osv):
	"""
	Represents FTP connection to ADS server.
	Call connect and disconnect to open and close.
	Call upload_data with an ads_data object to write data to the server.
	Call poll to download and import data from ADS to OpenERP
	"""

	_columns = {}
	_name = 'ads.connection'
	_auto = False

	_conn = None
	_vers_ads = 'VersADS'
	_vers_client = None

	@property
	def _connected(self):
		try:
			self._conn.voidcmd("NOOP")
			return True
		except:
			return False

	def _get_config(self, cr, config_name, value_type=str):
		"""
		Get a configuration value from ir.values by config_name (For this model)
		@param str config_name: The name of the ir.values record to get
		@param object value_type: Used to cast the value to an appropriate return type.
		"""
		values_obj = self.pool.get('ir.values')
		value_ids = values_obj.search(cr, 1, [('model','=','ads.connection'), ('name','=',config_name)])
		if value_ids:
			value = values_obj.browse(cr, 1, value_ids[0]).value_unpickle
			return value_type(value)
		else:
			return None

	def _get_ftp_config(self, cr):
		""" Save FTP connection parameters from ir.values to self """
		self._host = self._get_config(cr, 'ads_host') or 'ftp.alpha-d-s.com'
		self._port = self._get_config(cr, 'ads_port', int) or 21
		self._user = self._get_config(cr, 'ads_user')
		self._password = self._get_config(cr, 'ads_password')
		self._timeout = self._get_config(cr, 'ads_timeout', int) or 10
		self._mode = self._get_config(cr, 'ads_mode') or 'test'
		self._passive = self._get_config(cr, 'ads_passive', bool) or True

		assert self._mode in ['prod', 'test'], 'Mode must be either "prod" or "test"'

	def connect(self, cr):
		""" Sets up a connection to the ADS FTP server """
		if self._connected:
			return self

		self._get_ftp_config(cr)
		self._conn = FTP(host=self._host, user=self._user, passwd=self._password)

		# passive on by default in python > 2.1
		if not self._passive:
			self._conn.set_pasv(self._passive)

		# change directory to self._mode, then save "VersClient" dir name
		self.cd(self._mode)
		directories = self.ls()
		if len([d for d in directories if d != 'VersADS']) == 1:
			self._vers_client = [d for d in directories if d != 'VersADS'][0]
		elif 'Vers%s' % self._user in directories:
			self._vers_client = 'Vers%s' % self._user
		else:
			raise IOError('Could not find appropriate directories in %s folder.'\
						+ 'Normally there are VersADS and Vers*ClientName* directories' % self._mode)

		return self

	def disconnect(self):
		""" Closes a previously opened connection to the ADS FTP server """
		if self._connected:
			self._conn.quit()

	# ftp convenience methods
	def ls(self):
		if hasattr(self._conn, 'mlst'):
			return self._conn.mlsd()
		else:
			return self._conn.nlst()

	def cd(self, dirname):
		self._conn.cwd(dirname)

	def delete(self, filename):
		self._conn.delete(filename)

	def upload_data(self, data):
		"""
		Takes an ads_data object and creates an XML file then uploads it to FTP server
		@param ads_data data: Contains data to be written to the file
		"""
		assert isinstance(data, ads_data), 'data parameter must extend ads_data class'
		assert self._connected, 'Not connected to the FTP server'

		xml_buffer = data.generate_xml()
		self.cd(self._vers_ads)
		self._conn.storlines('STOR %s' % data.name(), xml_buffer)
		self.cd('..')

	def poll(self, cr, uid):
		"""	Poll the FTP server to parse and then delete any data files	"""
		if not self._connected:
			self.connect(cr)

		# get file list from VersADS
		self.cd(self._vers_client)
		files = self.ls()

		if files:
			for file_name in files:
				# get type prefix from file name, then find ads_data subclass with matching
				# type. Instantiate said class with XML as parameter to parse into dict
				data_type = file_name.split('-', 1)[0]
				class_for_type = [cls for cls in ads_data.__subclasses__() if cls.data_type == data_type]
				if class_for_type:
					file_data = StringIO.StringIO()
					self._conn.retrbinary('RETR %s' % file_name, file_data.write)
					data = class_for_type[0](file_data.getvalue())
					res = data.process(cr, uid)
					if res:
						self.delete(file_name)
					cr and cr.commit()
				else:
					raise TypeError('Could not find subclass of ads_data with data_type %s' % data_type)

		self.cd('..')
