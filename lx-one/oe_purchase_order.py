from copy import copy
from openerp.osv import osv,fields
from lx_purchase_order import lx_purchase_order
from oe_lx import oe_lx

def upload_po_picking(stock_picking_obj, cr, uid, picking_id, vals={}, context=None):
    """
    Extract and upload the picking to the server.
    If there is an exception it will be raised.
    """
    picking = stock_picking_obj.browse(cr, uid, picking_id, context=context)
    data = lx_purchase_order(picking)
    data.upload(cr, stock_picking_obj.pool.get('lx.manager'))

class stock_picking(oe_lx, osv.osv):
    """
    Inherit the stock.picking object to trigger upload of PO pickings
    """
    _inherit = 'stock.picking'
    
    def is_return(self, pick):
        """ Seems to be the only way to check if an IN is a return or not ... """
        return ('-' in pick.name and sorted(pick.name.split('-'), reverse=True)[0].startswith('ret')) 
    
    def action_assign_wkf(self, cr, uid, ids, context=None):
        """ Upload picking to LX1 """
        
        if not hasattr(ids, '__iter__'):
            ids = [ids]

        res = super(stock_picking, self).action_assign_wkf(cr, uid, ids, context=context)
    
        for picking_id in ids:
            picking = self.browse(cr, 1, picking_id, context=context)

            if picking.type.lower() == 'in' and not self.is_return(picking) and not picking.lx_sent:
                
                # detect if this picking is a partial
                pickings_for_po = self.search(cr, 1 ,[
                    ('purchase_id', '=', picking.purchase_id.id),
                    ('type', '=', 'in'),
                    ('state', 'not in', ['cancel']),
                ])
                is_partial = len(pickings_for_po) > 1
                
                if not is_partial:
                    upload_po_picking(self, cr, 1, picking_id, context=context)
                    
        return res
