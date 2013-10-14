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
	
	def _to_dict_recursive(self, nested_autoviv):
		nested_dict = {}
		for key in nested_autoviv:
			val = nested_autoviv[key]
			
			if type(val) == AutoVivification:
				nested_dict[key] = self._to_dict_recursive(dict(val))
			else:
				nested_dict[key] = val
		return nested_dict
	
	def to_dict(self):
		""" Converts a nested AutoVivification object to a nested dict """
		return self._to_dict_recursive(self)
