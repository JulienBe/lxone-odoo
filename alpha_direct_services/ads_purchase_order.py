from copy import copy
import logging
_logger = logging.getLogger(__name__)

from openerp.osv import osv
from openerp.tools.translate import _

from ads_data import ads_data
from tools import convert_date

class ads_purchase_order(ads_data):
    """
    Handles the extraction of a purchase order's picking.
    """

    file_name_prefix = ['FOUR']
    xml_root = 'COMMANDEFOURNISSEURS'
    _auto_remove = False

    def extract(self, picking):
        """
        Takes a stock.picking.in browse_record and extracts the
        appropriate data into self.data

        @param browse_record(stock.picking.in) picking: the stock picking browse record object
        """
        required_data = {
            'NUM_BL': 'This should never happen - please contact OpenERP',
            'DATE_PREVUE': 'Expected date',
            'LIBELLE_FOURN': 'Supplier name',
            'CODE_ART': 'Product reference (IP)',
            'QTE_ATTENDUE': 'Product quantity',
        }
        
        # create a template that contains data that does not change per PO line
        template = {
            'NUM_BL': picking.name,
            'DATE_PREVUE': convert_date(picking.purchase_id.minimum_planned_date),
            'LIBELLE_FOURN': picking.partner_id.name,
        }

        # iterate on move lines and use the template to create a data node that represents the PO line
        for move in picking.move_lines:
            if picking.partner_id.id in [seller.name.id for seller in move.product_id.seller_ids]:
                code_art_fourn = [seller.product_code for seller in move.product_id.seller_ids if seller.name.id == picking.partner_id.id][0]
            else:
                code_art_fourn = None

            po_data = copy(template)
            po_data['CODE_ART'] = move.product_id.x_new_ref
            po_data['CODE_ART_FOURN'] = code_art_fourn
            po_data['QTE_ATTENDUE'] = move.product_qty
            
            missing_data = {}
            for field in required_data:
                if not po_data[field]:
                    missing_data[field] = required_data[field]
            
            if missing_data:
                message = _('We are missing data for the following required fields:') + '\n\n' \
                            + "\n".join(sorted(['- ' + _(missing_data[data]) for data in missing_data]))\
                            + '\n\n' + _('These fields must be filled before we can continue')
                raise osv.except_osv(_('Missing Required Data'), message)
            
            self.insert_data('COMMANDEFOURNISSEUR', po_data)
            
        return self
