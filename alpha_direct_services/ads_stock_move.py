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

    def _extract_data(self):
        """
        Extracts self.data into a dictionary of importable data like so:
        {
            'IN' : {picking name, {product code: {quantity: qty moved, date: date moved}}}
            'OUT': {picking name, {product code: {quantity: qty moved, date: date moved}}}
        }
        """
        move_data = AutoVivification()

        for move in self.data['MvtStk']:

            # extract data from self.data into move_data dict
            if not 'TYPEMVT' in move:
                _logger.warn(_('A move has been skipped because it was missing the TYPEMVT field: %s' % move))

            move_date = 'DATEMVT' in move and move['DATEMVT'] or None
            product_code = 'CODE_ART' in move and move['CODE_ART'] or None
            quantity = 'QTE' in move and move['QTE'] or None
            picking_name = 'NUMBL' in move and move['NUMBL'] or None
            move_type = move['TYPEMVT']
            move_type = move_type == 'E' and 'IN' or 'OUT'

            move_data[move_type][picking_name][product_code]['quantity'] = quantity
            move_data[move_type][picking_name][product_code]['date'] = move_date

        return move_data

    def _process_po(self, pool, cr, picking_name, picking_lines, picking_type='in'):
        """ 
        Executes the reception wizard for the appropriate IN based on self.data received from ADS 
        """
        # vaidate params and find picking
        assert picking_name, _("A picking was received from ADS without a name, so we can't process it")

        picking_obj = pool.get('stock.picking')
        picking_id = picking_obj.search(cr, 1, [('name', '=', picking_name)])

        assert picking_id, _("No picking found with name %s" % picking_name)
        assert len(picking_id) == 1, _("Should have found exactly one picking with name %s" % picking_name)

        # set move_date to first not falsy date in picking_lines, or now()
        move_date = datetime.now().strftime(ads_date_format)
        for product_code in picking_lines:
            if picking_lines[product_code]['date']:
                move_date = picking_lines[product_code]['date'] 
                break

        # create a wizard record for this picking
        context = {
            'active_model': 'stock.picking.%s' % picking_type, 
            'active_ids': picking_id,
            'active_id': picking_id,
        }
        stock_partial_picking_obj = pool.get('stock.partial.picking')
        wizard_id = stock_partial_picking_obj.create(cr, 1, {'date': move_date}, context=context)
        wizard = stock_partial_picking_obj.browse(cr, 1, wizard_id)

        # For each move line in the wizard set the quantity to that received from ADS or 0
        for move in wizard.move_ids:
            if move.product_id.x_new_ref in picking_lines:
                pool.get('stock.partial.picking.line').write(cr, 1, move.id, 
                        {'quantity': picking_lines[product_code]['quantity']
                })
            else:
                pool.get('stock.partial.picking.line').write(cr, 1, move.id, {'quantity': 0})

        # Process receipt
        stock_partial_picking_obj.do_partial(cr, 1, [wizard_id])

    def _process_so(self, pool, cr, picking_name, picking_lines, picking_type='out'):
        """ 
        Executes the delivery wizard for the appropriate OUT based on self.data received from ADS 
        """
        # vaidate params and find picking
        assert picking_name, _("A picking was received from ADS without a name, so we can't process it")

        picking_obj = pool.get('stock.picking')
        picking_id = picking_obj.search(cr, 1, [('name', '=', picking_name)])

        assert picking_id, _("No picking found with name %s" % picking_name)
        assert len(picking_id) == 1, _("Should have found exactly one picking with name %s" % picking_name)

        # set move_date to first not falsy date in picking_lines, or now()
        move_date = datetime.now().strftime(ads_date_format)
        for product_code in picking_lines:
            if picking_lines[product_code]['date']:
                move_date = picking_lines[product_code]['date'] 
                break

        # create a wizard record for this picking
        context = {
            'active_model': 'stock.picking.%s' % picking_type, 
            'active_ids': picking_id,
            'active_id': picking_id,
        }
        wizard_obj = pool.get('stock.partial.picking')
        wizard_id = wizard_obj.create(cr, 1, {'date': move_date}, context=context)
        wizard = wizard_obj.browse(cr, 1, wizard_id)

        # For each move line in the wizard set the quantity to that received from ADS or 0
        for move in wizard.move_ids:
            if move.product_id.x_new_ref in picking_lines:
                pool.get('stock.partial.picking.line').write(cr, 1, move.id, 
                        {'quantity': picking_lines[product_code]['quantity']
                })
            else:
                pool.get('stock.partial.picking.line').write(cr, 1, move.id, {'quantity': 0})

        # Process receipt
        wizard_obj.do_partial(cr, 1, [wizard_id])
        pass

    def process(self, pool, cr):
        """
        Triggers _process_po or _process_so to handle the processing of a PO or SO picking.
        
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @returns True if successful. If True, the xml file on the FTP server will be deleted.
        """
        # Some data validation
        if 'MvtStk' not in self.data:
            return True

        if isinstance(self.data['MvtStk'], AutoVivification):
            self.data['MvtStk'] = [self.data['MvtStk']]

        # extract data into sets of move type, picking name and product codes
        move_data = self._extract_data()

        # iterate over extracted data and call appropriate self._process_XX
        for move_type in move_data:
            for picking_name in move_data[move_type]:
                if move_type == 'IN':
                    self._process_po(pool, cr, picking_name, move_data[move_type][picking_name], 'in')
                else:
                    self._process_so(pool, cr, picking_name, move_data[move_type][picking_name], 'out')

        return True
