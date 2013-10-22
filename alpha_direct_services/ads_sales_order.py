from copy import copy

from ads_data import ads_data
from ads_tools import convert_date

class ads_sales_order(ads_data):

	data_type = 'CMDE'
	xml_root = 'orders'

	def extract(self, picking):
		"""
		Takes a stock.picking.out browse_record and extracts the
		appropriate data into self.data

		@param picking: browse_record(stock.picking.in)
		"""
		shipping = picking.sale_id.partner_shipping_id
		invoice = picking.sale_id.partner_invoice_id
		
		self.insert_data('order.header', {
			'NUM_CMDE': picking.sale_id.name,
			'NUM_FACTURE_BL': picking.name,
			'DATE_EDITION': convert_date(picking.date),
			'MONTANT_TOTAL_TTC': picking.sale_id.amount_total,
		})
		self.insert_data('order.header.customer', {
			'name': picking.partner_id.name,
			'cust_num': picking.partner_id.ref or '',
		})
		self.insert_data('order.header.customer.shipping_address', {
			'name': not shipping.is_company and shipping.name or '',
			'corp_name': shipping.is_company and shipping.name or '',
			'adr1': shipping.street or '',
			'adr2': shipping.street2 or '',
			'country': shipping.country_id and shipping.country_id.name or '',
			'zip': shipping.zip or '',
			'city': shipping.city or '',
			'phone': shipping.phone or '',
			'email': shipping.email or '',
		})
		self.insert_data('order.header.customer.billing_address', {
			'adr1': invoice.street or '',
			'adr2': invoice.street2 or '',
			'country': invoice.country_id and invoice.country_id.name or '',
			'zip': invoice.zip or '',
			'city': invoice.city or '',
			'phone': invoice.phone or '',
			'email': invoice.email or '',
		})
		
		line_seq = 1
		for move in picking.move_lines:
			line = {
				'NUM_FACTURE_BL': picking.name,
				'CODE_ART': move.product_id.x_new_ref,
				'line_seq': line_seq,
				'QTE': move.product_qty,
				'LIBELLE_ART': move.product_id.name or '',
				'OBLIGATOIRE': '1',
			}
			self.insert_data('order.articles.line', line)
			line_seq += 1
		
		return self
