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
		shipping_partner = picking.sale_id.partner_shipping_id
		invoice_partner = picking.sale_id.partner_invoice_id
		
		self.insert_data('order', {
			# general
			'NUM_CMDE': picking.sale_id.name,
			'NUM_FACTURE_BL': picking.name,
			'DATE_EDITION': convert_date(picking.date),
			'MONTANT_TOTAL_TTC': picking.sale_id.amount_total,
			'DATE_ECHEANCE': convert_date(picking.min_date),

			# invoice_partner address and contact
			'SOCIETE_FAC': invoice_partner.is_company and invoice_partner.name or '',
			'NOM_CLIENT_FAC': not invoice_partner.is_company and invoice_partner.name or '',
			'ADR1_FAC': invoice_partner.street or '',
			'ADR2_FAC': invoice_partner.street2 or '',
			'CP_FAC': invoice_partner.zip or '',
			'VILLE_FAC': invoice_partner.city or '',
			'ETAT_FAC': invoice_partner.state_id and invoice_partner.state_id.name or '',
			'PAYS_FAC': invoice_partner.country_id and invoice_partner.country_id.name or '',
			'CODE_ISO_FAC': invoice_partner.country_id and invoice_partner.country_id.code or '',

			# delivery address and contact
			'SOCIETE_LIV': shipping_partner.is_company and shipping_partner.name or '',
			'NOM_CLIENT_LIV': not shipping_partner.is_company and shipping_partner.name or '',
			'ADR1_LIV': shipping_partner.street or '',
			'ADR2_LIV': shipping_partner.street2 or '',
			'CP_LIV': shipping_partner.zip or '',
			'VILLE_LIV': shipping_partner.city or '',
			'ETAT_LIV': shipping_partner.state_id and shipping_partner.state_id.name or '',
			'PAYS_LIV': shipping_partner.country_id and shipping_partner.country_id.name or '',
			'CODE_ISO_LIV': shipping_partner.country_id and shipping_partner.country_id.code or '',
			'TELEPHONE_LIV': shipping_partner.phone or '',
			'EMAIL_LIV': shipping_partner.email or '',
		})

		line_seq = 1
		for move in picking.move_lines:
			line = {
				'NUM_FACTURE_BL': picking.name,
				'CODE_ART': move.product_id.x_new_ref,
				'LIBELLE_ART': move.product_id.name or '',
				'QTE': move.product_qty,
				'OBLIGATOIRE': '1',
			}
			self.insert_data('order.articles.line', line)
			line_seq += 1

		return self
