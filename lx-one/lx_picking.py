from copy import deepcopy
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime

from openerp.tools.translate import _

from auto_vivification import AutoVivification
from lx_data import lx_data
from tools import parse_date

class lx_picking(lx_data):
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
        # iterate over extracted data and call self._process_picking
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
        backorder_ids = picking_obj.search(cr, 1, [('backorder_id', '=', picking_name), ('state', '=', 'assigned')])

        while(backorder_ids):
            picking = picking_obj.browse(cr, 1, backorder_ids[0])
            backorder_ids = picking_obj.search(cr, 1, [('backorder_id', '=', picking.name), ('state', '=', 'assigned')])

        if not picking:
            picking_ids = picking_obj.search(cr, 1, [('name', '=', picking_name), ('state', '=', 'assigned')])
            assert picking_ids, _("Could not find picking with name '%s' and state assigned" % picking_name)
            picking = picking_obj.browse(cr, 1, picking_ids[0])
            
        return picking.id

    def _process_picking(self, pool, cr, picking_name, picking_lines_original):
        """
        Executes the reception wizard for an IN or the delivery wizard for an out with
        data from self.data received from LX1
        @param pool: OpenERP object pool
        @param cursor cr: OpenERP database cursor
        @param str picking_name: Name of the picking to be processed
        @param list picking_lines: A list of picking move data. Refer to self._extract_to_process
        """
        # validate params and find picking
        if not picking_lines_original:
            return
        
        assert picking_name, _("A picking was received from LX1 without a name, so we can't process it")
        picking_id = self._find_picking(pool, cr, picking_name)
        assert picking_id, _("No picking found with name %s" % picking_name)
        picking = pool.get('stock.picking').browse(cr, 1, picking_id)
        assert picking.state != 'done', _("Picking '%s' (%d) has already been closed" % (picking_name, picking_id))

        # create working copy of picking_lines_original in case original is needed intact higher in the stack
        picking_lines = deepcopy(picking_lines_original)
        
        # set move_date to first not falsey date in picking_lines, or now()
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
        wizard_line_obj = pool.get('stock.partial.picking.line')
        wizard_id = wizard_obj.create(cr, 1, {'date': move_date}, context=context)
        wizard = wizard_obj.browse(cr, 1, wizard_id)
        
        # reset quantities received to zero
        wizard_line_obj.write(cr, 1, [move.id for move in wizard.move_ids], {'quantity': 0})

        # Consider: Picking with two lines same product x 1 and 5. Receive 5 on 1 and 1 on 5, 4 left over to deliver!        
        # Sort wizard moves and picking lines to have lowest quantity first so they are processed in that order.
        wizard.move_ids.sort(key=lambda move: move.move_id.product_qty)
        picking_lines.sort(key=lambda line: line['quantity'], reverse=True) # reverse order because they are reverse iterated
        
        # Iterate on wizard move lines setting quantity received to that in picking lines, or 0
        for move in wizard.move_ids:
            
            move_product_reference = move.product_id.x_new_ref
            move_quantity_ordered = move.move_id.product_qty
            remainder = None
            
            # process picking lines in reverse order, removing them at the end
            for picking_line_index in reversed(xrange(len(picking_lines))):
                picking_line = picking_lines[picking_line_index]
            
                # If picking line name matches move product x_new_ref, process picking_line quantity    
                if move_product_reference == picking_line['name']:

                    # If received qty > ordered qty and we have second picking line for same product, 
                    # set received qty to full and add remainder to next picking line                    
                    if picking_line['quantity'] > move_quantity_ordered \
                        and len([line for line in picking_lines if line['name'] == move_product_reference]) > 1:
                        
                        # Set move qty as full. Save remainder for next line
                        wizard_line_obj.write(cr, 1, move.id, {'quantity': move_quantity_ordered})
                        remainder = picking_line['quantity'] - move_quantity_ordered
                    
                    else:
                        # just write quantity on line
                        wizard_line_obj.write(cr, 1, move.id, {'quantity': picking_line['quantity']})
                    
                    # picking line processed so delete it from the list                    
                    del picking_lines[picking_line_index]
                    
                    # add remainder to next line
                    if remainder != None:
                        [line for line in picking_lines if line['name'] == move_product_reference][0]['quantity'] += remainder
                        remainder = None
  
                    # break when picking line is found for move, to avoid processing multiple picking lines on a single move                  
                    break
                    
        # Process receipt
        wizard_obj.do_partial(cr, 1, [wizard_id])
