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
    
    def action_assign(self, cr, uid, ids, context=None):
        """ Upload picking to LX1 """
        res = super(stock_picking, self).action_assign(cr, uid, ids, context=context)
        self.check_do_upload(cr, uid, ids, 'outgoing', lx_sales_order, context=context)
        return res
    
    def force_assign(self, cr, uid, ids, context=None):
        """ Upload the picking when forcing it to be assigned """
        res = super(stock_picking, self).force_assign(cr, uid, ids, context=context)
        self.check_do_upload(cr, uid, ids, 'outgoing', lx_sales_order, context=context)
        return res
    
    def check_do_upload(self, cr, uid, ids, picking_type_code, lx_data_subclass, context=None):
        """ 
        If state is assigned and the picking type code is picking_type_code, upload 
        @param picking_type_code: The code of the picking type [incoming, outgoing, internal]
        @param lx_data_subclass: The lx_data subclass that represents this object, i.e. lx_sales_order
        """
        for picking in self.browse(cr, 1, ids, context=context):
            
            if picking.picking_type_id.code == picking_type_code and picking.state == 'assigned':
                
                # if picking is outbound, ensure picking's sales_order has had an invoice created
                if picking.picking_type_id.code == 'outbound' and picking.sale_id.state != 'progress':
                    raise osv.except_osv(_("Sale Order Not Invoiced"), _("The sale order '%s' must be fully invoiced before the picking can be sent to LX1") % picking.sale_id.name)
                
                self.upload(cr, 1, picking, lx_data_subclass)
