from tools import parse_date

class lx_file(object):
	""" Represents a file received from LX1. Used for sorting processing priority """

	def __init__(self, file_name):
		""" Extracts file date and extension """
		super(lx_file, self).__init__()

		self.file_name = file_name

		if file_name.count('.') == 1:
			
			try:
				customer, file_sequence, extension = file_name.replace('.', '_').split('_')

				self.extension = extension.lower()
				self.customer = customer
				self.file_sequence = file_sequence
				self.valid = True
			except ValueError:
				self.valid = False
		else:
			self.valid = False

	def to_process(self):
		return (self.extension == 'xml')
