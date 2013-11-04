from copy import copy
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime

from openerp.tools.translate import _

from auto_vivification import AutoVivification
from ads_data import ads_data
from ads_tools import ads_date_format

class ads_stock_move(ads_data):
    file_name_prefix = ['MVTS']
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
        root_key = self.data.keys()[0]

        for move in self.data[root_key]:

            # extract data from self.data into move_data dict
            if not all([field in move for field in ['TYPEMVT', 'CODEMVT', 'NUMBL', 'CODE_ART', 'QTE']]):
                _logger.warn(_('A move has been skipped because it was missing a required field: %s' % move))
                continue

            picking_name = move['NUMBL']
            move_code = move['CODEMVT']
            move_type = move['TYPEMVT']
            move_type = move_type == 'E' and 'IN' or 'OUT'

            product_code = str(move['CODE_ART'])
            quantity = move['QTE']
            move_date = 'DATEMVT' in move and move['DATEMVT']

            # only extract PO IN's
            if picking_name and move_type == 'IN' and move_code in ['REC', 'Reception']:
                move_data[move_type][picking_name][product_code]['quantity'] = quantity
                move_data[move_type][picking_name][product_code]['date'] = move_date

        return move_data

    def _find_picking(self, pool, cr, picking_name):
        """
        Find's the most recent picking for an order. This will be the original picking
        if the picking has not been split, or the most recent split picking if it has.
        @return int: ID of the picking record
        """
        picking_obj = pool.get('stock.picking')
        picking = None
        backorder_ids = picking_obj.search(cr, 1, [('backorder_id', '=', picking_name)])

        while(backorder_ids):
            picking = picking_obj.browse(cr, 1, backorder_ids[0])
            backorder_ids = picking_obj.search(cr, 1, [('backorder_id', '=', picking.name)])

        if not picking:
            picking_ids = picking_obj.search(cr, 1, [('name', '=', picking_name)])
            assert picking_ids, _("Could not find picking with name '%s'" % picking_name)
            picking = picking_obj.browse(cr, 1, picking_ids[0])
        return picking.id

    def _process_picking(self, pool, cr, picking_name, picking_lines, picking_type):
        """
        Executes the delivery or reception wizard for the appropriate OUT or IN
        based on self.data received from ADS
        @param pool: OpenERP object pool
        @param cursor cr: OpenERP database cursor
        @param str picking_name: Name of the picking to be processed
        @param list picking_lines: A list of picking move data. Refer to self._extract_data
        @param str picking_type: 'in' or 'out' depending on type of picking to be processed
        """
        # vaidate params and find picking
        assert picking_name, _("A picking was received from ADS without a name, so we can't process it")
        assert picking_type in ['in', 'out'], _("Picking type must be either 'in' or 'out'")

        picking_id = self._find_picking(pool, cr, picking_name)

        assert picking_id, _("No picking found with name %s" % picking_name)

        # set move_date to first not falsy date in picking_lines, or now()
        move_date = datetime.now().strftime(ads_date_format)
        for product_code in picking_lines:
            if picking_lines[product_code]['date']:
                move_date = picking_lines[product_code]['date']
                break

        # create a wizard record for this picking
        context = {
            'active_model': 'stock.picking.%s' % picking_type,
            'active_ids': [picking_id],
            'active_id': picking_id,
        }
        wizard_obj = pool.get('stock.partial.picking')
        wizard_id = wizard_obj.create(cr, 1, {'date': move_date}, context=context)
        wizard = wizard_obj.browse(cr, 1, wizard_id)

        # For each move line in the wizard set the quantity to that received from ADS or 0
        for move in wizard.move_ids:
            if move.product_id.x_new_ref in picking_lines:
                pool.get('stock.partial.picking.line').write(cr, 1, move.id,
                    {'quantity': picking_lines[move.product_id.x_new_ref]['quantity']
                })
            else:
                pool.get('stock.partial.picking.line').write(cr, 1, move.id, {'quantity': 0})

        # Process receipt
        wizard_obj.do_partial(cr, 1, [wizard_id])

    def process(self, pool, cr):
        """
        Triggers _process_po or _process_picking to handle the processing of a PO or SO picking.

        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @returns True if successful. If True, the xml file on the FTP server will be deleted.
        """
        if not self.data:
            return True

        root_key = self.data.keys()[0]

        if isinstance(self.data[root_key], AutoVivification):
            self.data[root_key] = [self.data[root_key]]

        # extract data into sets of move type, picking name and product codes
        move_data = self._extract_data()

        # iterate over extracted data and call appropriate self._process_XX
        for move_type in move_data:
            for picking_name in move_data[move_type]:
                self._process_picking(pool, cr, picking_name, move_data[move_type][picking_name], move_type.lower())

        return True
