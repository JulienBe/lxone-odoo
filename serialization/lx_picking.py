from copy import deepcopy
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime

from openerp.tools.translate import _

from lx_data import lx_data
from openerp.addons.lx_one.tools import parse_date
from openerp.addons.lx_one import iso8601

class lx_picking(lx_data):
    """
    Handles the processing of incoming picking files to mark a picking as delivered 
    """

    object_type = ['OutboundService']

    def process(self, pool, cr, picking_data):
        """
        Triggers _process_picking to handle the processing of a PO or SO picking.
        Executes the reception wizard for an IN or the delivery wizard for an out with
        data from self.data received from LX1
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @param picking: The data for the picking to process. See _extract_to_process
        """
        picking_package = picking_data['out:OutboundShipmentLines']['out:OutboundShipmentPackageLine']
        picking_items = picking_data['out:OutboundShipmentLines']['out:OutboundShipmentItemLine']
        
        if len(picking_items) == 0:
            return
        
        picking_so = picking_items[0]['out:DeliveryOrder']['out:OrderReference']
        
        # make sure the order reference is the same for all picking item lines
        for picking_item in picking_items:
            if not picking_item['out:DeliveryOrder']['out:OrderReference'] == picking_so:
                raise ValueError('File from LX1 contains a mix of pickings from different sales orders. ' + \
                                 'More development must be done to cover this use case.')
        
        # validate the data        
        picking = self._find_picking(pool, cr, picking_so)
        assert picking.state != 'confirmed', _("Picking '%s' (%d) has not yet been confirmed" % (picking.name, picking.id))
        if picking.state == 'done':
            raise ValueError(_("Picking '%s' (%d) has already been transferred" % (picking.name, picking.id)))

        # set move_date to first not falsey date in picking_lines, or now()
        move_date = datetime.now()
        for picking_line in picking_items:
            if picking_line['out:ActualArrivalTime']:
                move_date = iso8601.parse_date(picking_line['out:ActualArrivalTime'])
                break
            
        # create a wizard record for this picking
        context = {
            'active_model': 'stock.picking',
            'active_ids': [picking.id],
            'active_id': picking.id,
        }
        wizard_obj = pool['stock.partial.picking']
        wizard_line_obj = pool['stock.partial.picking.line']
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
        
    def _find_picking(self, pool, cr, picking_so_name):
        """
        Return the browse record of the stock picking for the sale order. Will raise a ValueError
        if there are more or less than 1 picking found
        """
        so_id = pool['sale.order'].search(cr, 1, [('name', '=', picking_so_name)])
        if not so_id:
            raise ValueError(_('Could not find a sales order with name "%s"') % picking_so_name)
        pickings = pool['sale.order'].browse(cr, 1, so_id[0]).picking_ids
        if len(pickings) > 1:
            raise ValueError(_('Multiple pickings exist for the sale order "%s"') % picking_so_name)
        if len(pickings) == 0:
            raise ValueError(_('Could not find a stock picking for the sale order with name "%s"') % picking_so_name)
        return pickings[0]
