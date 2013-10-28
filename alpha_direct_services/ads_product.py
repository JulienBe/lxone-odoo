from copy import copy
from ads_data import ads_data

class ads_product(ads_data):

	file_name_prefix = ['ARTI']
	xml_root = 'flux_art'

	def extract(self, product):
		"""
		Takes a product browse_record and extracts the
		appropriate data into self.data

		@param browse_record(product.product) product: the stock product browse record object
		"""

		product_node = {
			'CODE_ART': product.ean13,
			'LIB_LONG': product.name or '',
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
