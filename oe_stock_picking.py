from ftplib import error_perm

from openerp.tools.translate import _
from openerp.osv import osv, fields

from lx_sales_order import lx_sales_order
from lx_purchase_order import lx_purchase_order
from oe_lx import oe_lx

def all_assigned(picking_obj, cr, ids):
    """ Returns true if all pickings have state 'assigned' """
    for picking in picking_obj.read(cr, 1, ids, ['state']):
        if picking['state'] != 'assigned':
            return False
    return True

class stock_picking(oe_lx, osv.osv):
    """
    Prevent manual processing
    """

    _inherit = 'stock.picking'
    _columns = {
        'create_date': fields.datetime('Create Date'),
    }

    def action_process(self, cr, uid, ids, context=None):
        if all_assigned(self, cr, ids):
            raise osv.except_osv(_('Cannot Process Manually'), _("The picking should be processed in the LX1 system. It will then be automatically synchronized to OpenERP."))
        else:
            super(stock_picking, self).action_process(cr, uid, ids, context=context)

class stock_picking_in(oe_lx, osv.osv):
    """ Inherit the stock.picking.in to prevent manual processing and cancellation after lx upload """

    _inherit = 'stock.picking'

    def lx_manuel_upload(self, cr, uid, ids, context=None):
        """ Upload this picking to LX1 """
        for picking_id in ids:
            picking = self.browse(cr, uid, picking_id, context=context)
            self.upload(cr, uid, picking, picking.type == 'in' and lx_purchase_order or lx_sales_order)
        return True
