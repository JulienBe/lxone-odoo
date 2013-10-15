#!/usr/bin/python

from ftplib import FTP
from ads_data import ads_data
import StringIO

class ads_conn(object):
	"""
	Represents FTP connection to ADS server.
	Call connect and disconnect to open and close.
	Call upload_data with an ads_data object to write data to the server.
	"""

	def __init__(self, host, port=None, user=None, password=None, timeout=None, mode='test', passive=True):
		super(ads_conn, self).__init__()
		assert mode in ['prod', 'test'], 'Mode must be either "prod" or "test"'
		
		self._host = host
		self._port = port
		self._user = user
		self._password = password
		self._timeout = timeout
		self._mode = mode
		self._passive = passive
		
		self._conn = None
		self._connected = False
		self._vers_ads = 'VersADS'
		self._vers_client = None

	def connect(self):
		""" Sets up a connection to the ADS FTP server """
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

		self._connected = True

	def disconnect(self):
		""" Closes a previously opened connection to the ADS FTP server """
		if self._connected:
			self._conn.quit()
			self._connected = False
	
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
		@param data ads_data: Contains data to be written to the file
		"""
		assert isinstance(data, ads_data), 'data parameter must extend ads_data class'
		assert self._connected, 'Not connected to the FTP server'

		xml_buffer = data.generate_xml()
		self.cd(self._vers_ads)
		self._conn.storlines('STOR %s' % data.name(), xml_buffer)
		self.cd('..')

	def poll(self, pool, cr, uid):
		"""	Poll the FTP server to parse and then delete any data files	"""
		assert self._connected, 'Not connected to the FTP server'

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
