import logging
_logger = logging.getLogger(__name__)
from datetime import datetime
import time
from openerp.tools.translate import _

from auto_vivification import AutoVivification
from ads_data import ads_data
from tools import convert_date, parse_date

class ads_sales_order(ads_data):
    """
    Handles the importation and exportation of a sales order's delivery order
    """

    file_name_prefix = ['CMDE', 'CREX']
    xml_root = 'orders'

    carrier_mapping = {
        'Lettre Max': '1',
        'Mondial Relay': '2',
        'Colissimo access - expert - international': '3',
        'Chronopost': '4',
        'EXAPAQ': '5',
        'GEODIS CALBERSON': '6',
        'DHL': '7'
    }

    def extract(self, picking):
        """
        Takes a stock.picking.out browse_record and extracts the
        appropriate data into self.data

        @param picking: browse_record(stock.picking.in)
        """
        shipping_partner = picking.sale_id.partner_shipping_id
        invoice_partner = picking.sale_id.partner_invoice_id
        carrier_name = picking.sale_id.carrier_id and picking.sale_id.carrier_id.name
        carrier_name = carrier_name and carrier_name in self.carrier_mapping and self.carrier_mapping[carrier_name] or ''

        if not picking.sale_id.carrier_id:
            _logger.warn('Could not map carrier %s to a valid value' % picking.sale_id.carrier_id.name)

        self.insert_data('order', {
            # general
            'NUM_CMDE': picking.sale_id.name,
            'NUM_FACTURE_BL': picking.name,
            'DATE_EDITION': convert_date(picking.date),
            'MONTANT_TOTAL_TTC': picking.sale_id.amount_total,
            'DATE_ECHEANCE': convert_date(picking.min_date),
            'TYPE_ENVOI': carrier_name,

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

    def process(self, pool, cr, expedition):
        """
        Receive sales orders in a CREX file
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @param AutoVivification expedition: Data from ADS describing the expedition of the SO
        """

        # extract information
        assert all([field in expedition for field in ['NUM_FACTURE_BL', 'STATUT']]), \
            'An expedition has been skipped because it was missing a required field: %s' % expedition

        picking_name = expedition['NUM_FACTURE_BL']
        status = expedition['STATUT']
        tracking_number = 'NUM_TRACKING' in expedition and expedition['NUM_TRACKING'] or ''
        send_date = 'DATE_EXPED' in expedition and expedition['DATE_EXPED'] and parse_date(expedition['DATE_EXPED']) or time.strftime("%Y%m%d")

        # ignore all but sent
        if status != 'E':
            return

        picking_obj = pool.get('stock.picking.out')
        picking_ids = picking_obj.search(cr, 1, [('name', '=', picking_name)])
        assert len(picking_ids) == 1, 'Should have found exactly 1 picking with name %s' % picking_name
        picking_id, = picking_ids
        assert picking_obj.browse(cr, 1, picking_id).state != 'done', _("Picking order with name '%s' is already done" % picking_name)

        # update OUT with tracking_number
        picking_obj.write(cr, 1, picking_id, {'carrier_tracking_ref': tracking_number})

        # create wizard and process delivery
        context = {
            'active_model': 'stock.picking.out',
            'active_ids': [picking_id],
            'active_id': picking_id,
        }
        wizard_obj = pool.get('stock.partial.picking')
        wizard_id = wizard_obj.create(cr, 1, {'date': send_date}, context=context)
        wizard_obj.do_partial(cr, 1, [wizard_id])
