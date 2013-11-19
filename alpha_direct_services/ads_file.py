from tools import parse_date

class ads_file(object):
	""" Represents a file received from ADS. Used for sorting processing priority """

	def __init__(self, file_name):
		""" Extracts file name prefix, date and extension """
		super(ads_file, self).__init__()

		self.file_name = file_name

		if '-' in file_name and '.' in file_name and file_name.count('.') == 1:
			
			try:
				prefix, date = file_name.split('-', 1)
				date, extension = date.split('.')

				self.date_string = date
				self.date = parse_date(date)
				self.prefix = prefix
				self.extension = extension.lower()
				self.valid = True
			except ValueError:
				self.valid = False
		else:
			self.valid = False

	def to_process(self):
		return (self.extension == 'xml')
