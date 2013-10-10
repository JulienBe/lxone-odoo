from ftplib import FTP

class ads_conn(object):
	"""
	Represents FTP connection to ADS server
	"""

	host = None
	port = None
	user = None
	password = None
	timeout = None
	conn = None

	def __init__(self, host, port=None, user=None, password=None, timeout=None):
		super(ads_conn, self).__init__()
		self.host = host
		self.port = port
		self.user = user
		self.timeout = timeout
		self.password = password

	def connect(self):
		""" Sets up a connection to the ADS FTP server """
		self.conn = FTP(self.host, self.user, self.password, self.timeout)
		self.conn.login()

	def disconnect(self):
		""" Closes a previously opened connection to the ADS FTP server """
		self.conn.quit()

	def write_data(self, data):
		"""
		Takes an ads_data object and creates an XML file then uploads it to FTP server
		@param data ads_data: Contains data to be written to the file
		"""
		assert isinstance(data, ads_data), 'data parameter must extend ads_data class'


from lxml import etree
import re

class ads_data(object):
	"""
	Store data to be uploaded to the ADS FTP server.
	Inherit this class to represent different types of data.
	Populate the fields dictionary with key = field name, value = data format:

	A20 : Alpha numeric where 20 is the character limit, left aligned and padded with spaces
 	N   : Numerique without commas, 12 caracteres right aligned padded with 0's

 	For example:

 	fields = {'product_code', 'A15'} <-- this will allow a 15 character alpha numeric product code
 	fields = {'product_number', 'N'} <-- this will allow a 12 character numeric product number

 	Create an instance of this class for each row of data for which you want an XML file.
 	Then populate the data dictionary with key = field name, value = field value
	"""

	fields = {}
	data = {}

	def __init__(self, data={}):
		super(ads_data, self).__init__()
		self.data = data

	def _validate_alphanumeric(self, s):
		""" Returns True if s is alpha numberic """
		return re.match('^[\w-_]+$', s)

	def _validate_data_types(self):
		""" 
		Validates that the data in self.data conforms to the self.field definitions
		@Raises assertion exception if there is a format problem
		"""
		for field_name in self.data:
			field_value = self.data(field_name)
			field_format = self.fields(field_name)

			field_type = field_format[0:1]
			field_length = field_format[1:] if len(field_format) > 1 else 0

			assert field_type in ['A', 'N'], \
				'Field definition "%s" does not conform to standards. See documentation' % field_name
			assert not (field_type == 'N' and field_length), \
				'Field definition "%s" does not conform to standards. See documentation' % field_name

			if field_type == 'A':
				assert _validate_alphanumeric(field_value), 'Data must be alphanumeric: %s' % field_value
				assert len(field_value) <= field_length, 'Data must be equal to or less than %s. Actual length is %d' % (field_length, len(field_value))
			elif field_type == 'N':
				assert len(field_value <= 12)

		print 'TODO: implement padding and alignment checks'
	
	def generate_xml(self):
		""" Returns an XML file compliant with the format that ADS is expecting """
		_validate_data_types()
		pass