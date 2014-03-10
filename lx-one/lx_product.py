from openerp import osv
from openerp.tools.translate import _
from copy import copy
from lx_data import lx_data

class lx_product(lx_data):

	file_name_prefix = ['ARTI']
	xml_root = 'flux_art'

	required_fields = [
		'name',
		'ean13',
		'uom_id',
	]

	def extract(self, product):
		"""
		Takes a product browse_record and extracts the
		appropriate data into self.data

		@param browse_record(product.product) product: the product browse record object
		"""
		assert product.uom_id.lx_ref, _("Unit of Measure '%s' is missing an LX Reference") % product.uom_id.name
		
		product_node = {
			'Client': 'pvszmd',
			'Item': product.ean13,
			'Description': product.name,
			'QuantityProperties': {
				'StandardUOM': product.uom_id.lx_ref,
			},
		}

		self.insert_data('ItemMasterCreate', product_node)
