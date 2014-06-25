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
        return super(sale_order, self).write(cr, uid, ids, vals, context=context)
        
    def create(self, cr, uid, vals, context=None):
        if 'picking_policy' in vals:
            vals['picking_policy'] = 'one'
        if 'order_policy' in vals:
            vals['order_policy'] = 'manual'
        return super(sale_order, self).create(cr, uid, vals, context=context)

class stock_picking(oe_lx, osv.osv):
    """
    Define do_upload_so method to be called by stock move confirmation
    """
    _inherit = 'stock.picking'
    
    def do_upload_so(self, cr, uid, picking, context=None):
        """ Raise an error if the sales order is not yet invoiced. Otherwise, upload """
        if picking.sale_id.state != 'progress':
            raise osv.except_osv(_("Sale Order Not Invoiced"), _("The sale order '%s' must be fully invoiced before the picking can be sent to LX1") % picking.sale_id.name)
        self.upload(cr, 1, picking, lx_sales_order)
