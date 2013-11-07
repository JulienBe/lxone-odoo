from copy import copy, deepcopy
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime

from openerp.tools.translate import _

from auto_vivification import AutoVivification
from ads_data import ads_data
from tools import convert_date, parse_date

class ads_purchase_order(ads_data):
    """
    Handles the extraction and uploading, and the downloading and importation
    of a purchase order's delivery order.
    """

    file_name_prefix = ['FOUR', 'MVTS']
    xml_root = 'COMMANDEFOURNISSEURS'
    _auto_remove = False

    def extract(self, picking):
        """
        Takes a stock.picking.in browse_record and extracts the
        appropriate data into self.data

        @param browse_record(stock.picking.in) picking: the stock picking browse record object
        """
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

            data = copy(template)
            data['CODE_ART'] = move.product_id.x_new_ref
            data['CODE_ART_FOURN'] = code_art_fourn
            data['QTE_ATTENDUE'] = move.product_qty
            self.insert_data('COMMANDEFOURNISSEUR', data)

        return self

    def pre_process_hook(self, pool, cr):
        # make backup copy of self.data, then replace self.data with a parsed version
        self.data_from_xml = deepcopy(self.data)
        self.data = self._extract_to_process()

    def process(self, pool, cr, picking):
        """
        Triggers _process_picking to handle the processing of a PO picking.

        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @param picking: The data for the picking to process. See _extract_to_process
        """
        # iterate over extracted data and call appropriate self._process_XX
        picking_name = picking.keys()[0]
        picking_lines = picking[picking_name]
        self._process_picking(pool, cr, picking_name, picking_lines)

        # remove all elements with NUMBL == picking_name from self.data_from_xml
        root_key = self.data_from_xml.keys()[0]
        self.data_from_xml[root_key] = [move for move in self.data_from_xml[root_key] if move['NUMBL'] != picking_name]

    def post_process_hook(self, pool, cr):
        self.data = self.data_from_xml

    def _extract_to_process(self):
        """
        Organises self.data into a batch of data that can be imported per picking
        @return: {'Pickings': [{'picking_name': [{'product_code': .., 'quantity': .., 'date': ..}]]}
        """
        move_data = AutoVivification({'Pickings': []})
        root_key = self.data.keys()[0]

        for move in self.data[root_key]:

            # extract data from self.data into move_data dict
            if not all([field in move for field in ['TYPEMVT', 'CODEMVT', 'NUMBL', 'CODE_ART', 'QTE']]):
                _logger.warn(_('A move has been skipped because it was missing a required field: %s' % move))
                continue

            picking_name = move['NUMBL']
            move_code = move['CODEMVT']
            move_type = move['TYPEMVT']
            move_type = move_type == 'E' and 'in' or 'out'

            product_code = str(move['CODE_ART'])
            quantity = move['QTE']
            move_date = 'DATEMVT' in move and move['DATEMVT']

            # only extract PO IN's
            if move_type == 'in' and move_code in ['REC', 'Reception']:
                line_vals = {'name': product_code, 'quantity': quantity, 'date': move_date}
                
                # try to find an existing list for picking_name. If found, append our data, otherwise create it
                target = [picking for picking in move_data['Pickings'] if picking.keys()[0] == picking_name]
                if not target:
                    move_data['Pickings'].append({picking_name: [line_vals]})
                else:
                    target[0][picking_name].append(line_vals)

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

    def _process_picking(self, pool, cr, picking_name, picking_lines):
        """
        Executes the reception wizard for an IN based on self.data received from ADS
        @param pool: OpenERP object pool
        @param cursor cr: OpenERP database cursor
        @param str picking_name: Name of the picking to be processed
        @param list picking_lines: A list of picking move data. Refer to self._extract_to_process
        """
        # vaidate params and find picking
        assert picking_name, _("A picking was received from ADS without a name, so we can't process it")
        picking_id = self._find_picking(pool, cr, picking_name)
        assert picking_id, _("No picking found with name %s" % picking_name)
        picking = pool.get('stock.picking').browse(cr, 1, picking_id)
        assert picking.state != 'done', _("Picking '%s' (%d) has already been closed" % (picking_name, picking_id))

        # set move_date to first not falsy date in picking_lines, or now()
        move_date = datetime.now()
        for picking_line in picking_lines:
            if picking_line['date']:
                move_date = parse_date(picking_line['date'])
                break

        # create a wizard record for this picking
        context = {
            'active_model': 'stock.picking.in',
            'active_ids': [picking_id],
            'active_id': picking_id,
        }
        wizard_obj = pool.get('stock.partial.picking')
        wizard_id = wizard_obj.create(cr, 1, {'date': move_date}, context=context)
        wizard = wizard_obj.browse(cr, 1, wizard_id)

        # For each move line in the wizard set the quantity to that received from ADS or 0
        for move in wizard.move_ids:
            if move.product_id.x_new_ref in [line['name'] for line in picking_lines]:
                pool.get('stock.partial.picking.line').write(cr, 1, move.id,
                    {'quantity': sum([line['quantity'] for line in picking_lines if line['name'] == move.product_id.x_new_ref])
                })
            else:
                pool.get('stock.partial.picking.line').write(cr, 1, move.id, {'quantity': 0})

        # Process receipt
        wizard_obj.do_partial(cr, 1, [wizard_id])

