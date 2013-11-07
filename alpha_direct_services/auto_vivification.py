class AutoVivification(dict):
	"""
	Implementation of perl's autovivification feature.
	Allows auto creation of nested dictionaries 
	along with some helper methods, for example:

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
			
			if isinstance(val, AutoVivification):
				nested_dict[key] = self._to_dict_recursive(dict(val))
			elif isinstance(val, (list, tuple)):
				new_list = []
				for element in val:
					new_list.append(self._to_dict_recursive(element))
				nested_dict[key] = new_list
			else:
				nested_dict[key] = val
		return nested_dict
	
	def to_dict(self):
		""" Converts a nested AutoVivification object to a nested dict """
		return self._to_dict_recursive(self)

	@staticmethod
	def _dict_to_auto_viv_recursive(nested_dict):
		nested_autoviv = AutoVivification()
		for key in nested_dict:
			val = nested_dict[key]
			
			if type(val) == dict:
				nested_autoviv[key] = AutoVivification._dict_to_auto_viv_recursive(AutoVivification(val))
			else:
				nested_autoviv[key] = val
		return nested_autoviv
	
	@staticmethod
	def dict_to_auto_vivification(dictionary):
		""" Converts a nested dictionary object to a nested AutoVivification """
		return AutoVivification._dict_to_auto_viv_recursive(dictionary)
