#!/usr/bin/python

from ftplib import FTP
from ads_data import ads_data

class ads_conn(object):
	"""
	Represents FTP connection to ADS server.
	Call connect and disconnect to open and close.
	Call upload_data with an ads_data object to write data to the server.
	"""

	_host = None
	_port = None
	_user = None
	_password = None
	_timeout = None
	_conn = None
	_connected = False

	def __init__(self, host, port=None, user=None, password=None, timeout=None):
		super(ads_conn, self).__init__()
		self._host = host
		self._port = port
		self._user = user
		self._timeout = timeout
		self._password = password

	def connect(self):
		""" Sets up a connection to the ADS FTP server """
		self._conn = FTP(host=self._host, user=self._user, passwd=self._password)
		self._conn.login(self._user, self._password)
		self._connected = True

	def disconnect(self):
		""" Closes a previously opened connection to the ADS FTP server """
		self._conn.quit()
		self._connected = False

	def upload_data(self, data):
		"""
		Takes an ads_data object and creates an XML file then uploads it to FTP server
		@param data ads_data: Contains data to be written to the file
		"""
		assert isinstance(data, ads_data), 'data parameter must extend ads_data class'
		assert self._connected, 'Not connected to the FTP server'

		xml = data.generate_xml()
		print xml
		print 'TODO: upload xml file'
