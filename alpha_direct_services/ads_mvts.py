from copy import deepcopy
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime

from openerp.tools.translate import _

from auto_vivification import AutoVivification
from ads_data import ads_data
from tools import parse_date

class ads_mvts(ads_data):
    """
    Handles the processing of MVTS files to receive a purchase order or deliver a sales order
    """

    file_name_prefix = ['MVTS']
    xml_root = 'mvts'
    _auto_remove = False
    pre_process_errors = []

    def pre_process_hook(self, pool, cr):
        """ Lets us process self.data in batches per picking """
        self.data_from_xml = deepcopy(self.data)
        self.data = self._extract_to_process()
        return self.pre_process_errors

    def process(self, pool, cr, picking):
        """
        Triggers _process_picking to handle the processing of a PO or SO picking.

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
        """ Lets us process self.data in batches per picking """
        try:
            self.data = self.data_from_xml
            return []
        except Exception as e:
            return ['%s: %s' % (type(e), unicode(e))]

    def _extract_to_process(self):
        """
        Organises self.data into a batch of data that can be imported per picking.
        @return: {'Pickings': [{'picking_name': [{'product_code': .., 'quantity': .., 'date': ..}]]}
        """
        move_data = AutoVivification({'Pickings': []})
        root_key = self.data.keys()[0]

        for move in self.data[root_key]:
            
            # catch exception per data node and save it in self.post_process_errors to return up a level
            try:

                # extract data from self.data into move_data dict
                assert all([field in move and move[field] for field in ['TYPEMVT', 'CODEMVT', 'CODE_ART', 'QTE']]), \
                    _('This move has been skipped because it was missing a required field: %s' % move)
    
                picking_name = 'NUMBL' in move and move['NUMBL'] or ''
                
                # ignore MVTS without a num bl as they are manual corrections which are represented anyway in STOC files
                if not picking_name:
                    continue
                
                assert picking_name, _("Must have a picking name (NUMBL) for moves whose CODEMVT is not REG")
                
                move_type = move['TYPEMVT']
                move_type = move_type == 'E' and 'in' or 'out'
    
                product_code = str(move['CODE_ART'])
                quantity = move['QTE']
                move_date = 'DATEMVT' in move and move['DATEMVT']
                
                assert picking_name, _('Picking name (NUMBL field) must have a value for node %s') % move
                assert move['TYPEMVT'] in ['E', 'S'], _('Move type (TYPEMVT field) must be either E or S for picking %s') % picking_name
                assert product_code, _('Product code (CODE_ART field) must have a value for picking %s') % picking_name
                
                # if MVTS is for an OUT, quantity will be negative so make it positive
                if move_type == 'out':
                    quantity = quantity * -1
    
                line_vals = {'name': product_code, 'quantity': quantity, 'date': move_date, 'move_type': move_type}
                
                # try to find an existing list for picking_name. If found, append our data, otherwise create it
                target = [picking for picking in move_data['Pickings'] if picking.keys()[0] == picking_name]
                if not target:
                    move_data['Pickings'].append({picking_name: [line_vals]})
                else:
                    target[0][picking_name].append(line_vals)
                    
            except Exception as e:
                self.pre_process_errors.append('%s: %s' % (type(e), unicode(e)))

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
            
        # if picking is canceled, find another one
        if picking.state in ['done','cancel']:
            picking_ids = picking_obj.search(cr, 1, [('sale_id','=',picking.sale_id.id),('state','not in',['done','cancel'])])
            picking = picking_obj.browse(cr, 1, sorted(picking_ids)[0])
        
        return picking.id

    def _process_picking(self, pool, cr, picking_name, picking_lines):
        """
        Executes the reception wizard for an IN or the delivery wizard for an out with
        data from self.data received from ADS
        @param pool: OpenERP object pool
        @param cursor cr: OpenERP database cursor
        @param str picking_name: Name of the picking to be processed
        @param list picking_lines: A list of picking move data. Refer to self._extract_to_process
        """
        # vaidate params and find picking
        if not picking_lines:
            return
        
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
            'active_model': 'stock.picking.%s' % picking_lines[0]['move_type'],
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
            elif not move.product_id.discount:
                pool.get('stock.partial.picking.line').write(cr, 1, move.id, {'quantity': 0})
            else:
                # automatically fully receive discount products
                pool.get('stock.partial.picking.line').write(cr, 1, move.id, {'quantity': move.move_id.product_qty})

        # Process receipt
        wizard_obj.do_partial(cr, 1, [wizard_id])
