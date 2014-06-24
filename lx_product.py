from copy import copy
from collections import OrderedDict

from openerp import osv
from openerp.tools.translate import _

from lx_data import lx_data

class lx_product(lx_data):

	object_type = ['ARTI']
	message_identifier = 'OpenErpItemCreate'

	required_fields = [
		'name',
		'ean13',
		'uom_id',
	]

	def extract(self, products):
		"""
		Takes a product browse_record or list of product browse_record's
		and extracts the appropriate data into self.data

		@param browse_record(product.product) product: the product browse record object
		"""
		if not isinstance(products, list):
			products = [products]
		
		self.data = OrderedDict([('ItemMasterCreate',[])])
		
		for product in products:
			product_dict = OrderedDict([
							('Client', 'pvszmd'),
							('Item', product.ean13),
							('Description', product.name),
							('QuantityProperties', OrderedDict([
								('StandardUOM', 'STCK'),
							])),
						])
			self.data['ItemMasterCreate'].append(product_dict)
		
		return True
