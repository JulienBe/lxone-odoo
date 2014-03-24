from openerp.osv import osv
from openerp.tools.translate import _

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
    
    def write(self, cr, uid, ids, vals, context=None):
        if 'picking_policy' in vals:
            vals['picking_policy'] = 'one'
        if 'order_policy' in vals:
            vals['order_policy'] = 'manual'
        super(sale_order, self).write(cr, uid, ids, vals, context=context)
        
    def create(self, cr, uid, vals, context=None):
        if 'picking_policy' in vals:
            vals['picking_policy'] = 'one'
        if 'order_policy' in vals:
            vals['order_policy'] = 'manual'
        return super(sale_order, self).create(cr, uid, vals, context=context)

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
                # ensure picking's sales_order has had an invoice created
                if picking.sale_id.state != 'progress':
                    raise osv.except_osv(_("Sale Order Not Invoiced"), _("The sale order '%s' must be fully invoiced before the picking can be sent to LX1") % picking.sale_id.name)
                
                self.upload(cr, 1, picking, lx_sales_order)

        return res

class stock_pickin_out(oe_lx, osv.osv):
    """
    Disallow creation of pickings without a sale order
    """
    _inherit = 'stock.picking.out'
    
    def create(self, cr, uid, vals, context=None):
        """ Don't allow manual creation of picking (without sale_id) """
        if vals.get('type') == 'out' and not vals.get('sale_id'):
            raise osv.except_osv(_("Missing Sale ID"), _("Delivery orders should always be created automatically by a sales order"))
        return super(stock_pickin_out, self).create(cr, uid, vals, context=context)
