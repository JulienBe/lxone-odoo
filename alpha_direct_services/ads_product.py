from openerp import osv
from openerp.tools.translate import _
from copy import copy
from ads_data import ads_data

class ads_product(ads_data):

	file_name_prefix = ['ARTI']
	xml_root = 'flux_art'

	uploaded_fields = ['x_new_ref',
						'name',
						'type',
						'ean13',
						'sale_delay',
						'x_depth',
						'x_width',
						'x_height',
						'weight_net',
						'x_url']

	def extract(self, product):
		"""
		Takes a product browse_record and extracts the
		appropriate data into self.data

		@param browse_record(product.product) product: the stock product browse record object
		"""

		if not product.x_new_ref:
			raise osv.except_osv(_("Product Missing Reference IP"), _("You have to enter a Reference IP for the product '%s' before you can continue" % product.name))

		product_node = {
			'CODE_ART': product.x_new_ref,
			'LIB_LONG': product.name,
			'TYPE_ART': product.type or '',
			'CAT_ART': 'PRO',
			'ART_PHYSIQUE': (product.type != 'service'),
			'EAN': product.ean13 or '',
			'DELAIVENTE': product.sale_delay or 0,
			'LONGUEUR': product.x_depth or 0,
			'LARGEUR': product.x_width or 0,
			'HAUTEUR': product.x_height or 0,
			'POIDS': product.weight_net or 0,
			'URL': product.x_url or '',
		}

		self.insert_data('PRODUCT', product_node)
