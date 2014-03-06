from copy import copy
from openerp.osv import osv,fields
from lx_test import lx_test
from oe_lx import oe_lx

class stock_picking_in(oe_lx, osv.osv):
    """
    Test oe hooks
    """
    _inherit = 'stock.picking.in'
    
    def draft_force_assign(self, cr, uid, ids, *args):
        """ Triggered by clicking confirm button on manually created IN """
        super(stock_picking_in, self).draft_force_assign(cr, uid, ids, *args)
        for picking_id in ids:
            picking = self.browse(cr, uid, picking_id)
            self.upload(cr, uid, picking, lx_test)
            
class stock_picking(oe_lx, osv.osv):
    """
    Test oe hooks
    """
    _inherit = 'stock.picking'
