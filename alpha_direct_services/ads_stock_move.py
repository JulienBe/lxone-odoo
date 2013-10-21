from copy import copy
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime

from openerp.tools.translate import _

from auto_vivification import AutoVivification
from ads_data import ads_data
from ads_tools import ads_date_format

class ads_stock_move(ads_data):
    data_type = 'MVTS'
    xml_root = 'adsxml'

    def process(self, pool, cr):
        """
        Executes the reception wizard for the appropriate IN based on self.data received from ADS
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @returns True if successful. If True, the xml file on the FTP server will be deleted.
        """
        # {picking name, {product code: {quantity: qty moved, date: date moved}}}
        move_data = AutoVivification()

        # Some data validation
        if 'MvtStk' not in self.data:
            return True

        if isinstance(self.data['MvtStk'], AutoVivification):
            self.data['MvtStk'] = [self.data['MvtStk']]

        # extract data from self.data into move_data dict        
        for move in self.data['MvtStk']:

            assert 'CODEMVT' in move and 'TYPEMVT' in move, _("The move must include either CODEMVT or TYPEMVT")
            if not (move['CODEMVT'] in ['Reception', 'REC']) or (move['TYPEMVT'] != 'E'):
                continue

            move_date = 'DATEMVT' in move and move['DATEMVT'] or None
            product_code = 'CODE_ART' in move and move['CODE_ART'] or None
            quantity = 'QTE' in move and move['QTE'] or None
            picking_name = 'NUMBL' in move and move['NUMBL'] or None

            move_data[picking_name][product_code]['quantity'] = quantity
            move_data[picking_name][product_code]['date'] = move_date

        # create stock.partial.picking wizards, write receipt details to move lines and process
        for picking_name in move_data:

            picking_obj = pool.get('stock.picking')
            picking_id = picking_obj.search(cr, 1, [('name','=',picking_name)])

            if not picking_id:
                _logger.error(_('Could not find stock.picking with the name "%s"' % picking_name))
                return False
            if len(picking_id) > 1:
                _logger.error(_("Should have found exactly 1 picking_id with name %s. We have %s" % (picking_name, len(picking_id))))

            move_date = datetime.now().strftime(ads_date_format)
            for product_code in move_data[picking_name]:
                if move_data[picking_name][product_code]['date']:
                    move_date = move_data[picking_name][product_code]['date'] 
                    break

            context = {'active_model': 'stock.picking.in', 'active_ids': picking_id}
            stock_partial_picking_obj = pool.get('stock.partial.picking')
            wizard_id = stock_partial_picking_obj.create(cr, 1, {'date': move_date}, context=context)
            wizard = stock_partial_picking_obj.browse(cr, 1, wizard_id)

            # For each move line in the wizard set the quantity to that received from ADS or 0             
            for move in wizard.move_ids:
                if move.product_id.x_new_ref in move_data[picking_name]:
                    pool.get('stock.partial.picking.line').write(cr, 1, move.id, 
							{'quantity': move_data[picking_name][product_code]['quantity']
					})
                else:
                    pool.get('stock.partial.picking.line').write(cr, 1, move.id, {'quantity': 0})

            # Process receipts            
            stock_partial_picking_obj.do_partial(cr, 1, [wizard_id])

        return True
