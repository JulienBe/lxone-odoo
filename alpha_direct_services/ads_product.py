#!/usr/bin/python

from copy import copy
from ads_data import ads_data

class ads_product(ads_data):

	data_type = 'ARTI'
	xml_root = 'flux_art'

	def extract(self, product):
		"""
		Takes a product browse_record and extracts the
		appropriate data into self.data

		@param browse_record(product.product) product: the stock product browse record object
		"""

		product_node = {
			'CODE_ART': product.x_new_ref,
			'LIB_LONG': product.name or '',
			'TYPE_ART': product.type or '',
			'CAT_ART': 'PRO',
			'ART_PHYSIQUE': (product.type != 'service'),
			'EAN': product.ean13 or '',
			'DELAIVENTE': product.sale_delay,
			'LONGUEUR': product.x_depth,
			'LARGEUR': product.x_width,
			'HAUTEUR': product.x_height,
			'POIDS': product.weight_net,
			'URL': product.x_url or '',
		}

		self.insert_data('PRODUCT', product_node)
