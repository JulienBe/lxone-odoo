from openerp.osv import osv

from lx_sales_order import lx_sales_order
from oe_lx import oe_lx

class sale_order(osv.osv):
    """ 
    Ensure picking policy = 'one', meaning picking is availble only when all lines are too 
    Ensure order policy = 'manual' meaning invoice is created manually
    """
    _inherit = 'sale.order'
    _defaults = {
        'picking_policy': 'one',
        'order_policy': 'manual',
    }
    
    def write(self, cr, uid, vals, ids, context=None):
        if 'picking_policy' in vals:
            vals['picking_policy'] = 'one'
        if 'order_policy' in vals:
            vals['order_policy'] = 'manual'
        super(sale_order, self).write(cr, uid, vals, ids, context=context)
        
    def create(self, cr, uid, vals, context=None):
        if 'picking_policy' in vals:
            vals['picking_policy'] = 'one'
        if 'order_policy' in vals:
            vals['order_policy'] = 'manual'
        super(sale_order, self).create(cr, uid, vals, context=context)

class stock_picking(oe_lx, osv.osv):
    """
    Inherit the stock.picking object to trigger upload of SO pickings
    """
    _inherit = 'stock.picking'

    def action_assign_wkf(self, cr, uid, ids, context=None):
        """ Upload picking to LX1 """
        res = super(stock_picking, self).action_assign_wkf(cr, uid, ids, context=context)

        for picking_id in ids:
            picking = self.browse(cr, 1, picking_id, context=context)

            if picking.type.lower() == 'out':
                self.upload(cr, 1, picking, lx_sales_order)

        return res
