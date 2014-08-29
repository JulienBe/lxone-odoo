from tools import parse_date
import logging
import traceback

_logger = logging.getLogger(__name__)

class lx_file(object):
	""" 
	Represents an xml file on the ftp server of LX1. 
	Used for sorting processing priority 
	"""

	def __init__(self, file_name):
		""" Saves the file name and calls _extract_file_name """
		super(lx_file, self).__init__()
		self.file_name = file_name
		self.customer = self.extension = self.file_sequence = None
		self._extract_file_name()

	def _extract_file_name(self):
		""" 
		Gets the extension, customer, file_sequence information out of a filename 
		and saves it to the self. 
		"""
		if self.file_name.count('.') == 1 and self.file_name.count('_') > 0:
			try:
				values = self.file_name.replace('.', '_').split('_')
				self.extension = values.pop().lower()
				self.file_sequence = values.pop()
				self.customer = "_".join(values)
			except ValueError as ex:
				_logger.warn('File ignored from FTP server while polling because of an exception: %s' % self.file_name)
				_logger.warn(traceback.format_exc())
		else:
			_logger.warn('File ignored from FTP server because of unconventional name: %s' % self.file_name)

	@property
	def valid(self):
		return self.customer is not None and self.extension is not None and self.file_sequence is not None
	
	def to_process(self):
		return self.customer.lower() != 'openerp' and self.extension == 'xml'
