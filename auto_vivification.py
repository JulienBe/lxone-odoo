class AutoVivification(dict):
	"""
	Implementation of perl's autovivification feature.
	Allows auto creation of nested dictionaries, for example:

		a = AutoVivification()
		a['order']['customer']['address']['roadname'] = 'Avenue Louise, 42'
		print a
		>>> {'order': {'customer': {'address': {'roadname': 'Avenue Louise, 42'}}}}
	"""
	def __getitem__(self, item):
		try:
			return dict.__getitem__(self, item)
		except KeyError:
			value = self[item] = type(self)()
			return value
