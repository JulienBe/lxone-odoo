from openerp.osv import osv

from lx_purchase_order import lx_purchase_order
from oe_lx import oe_lx

class stock_picking(oe_lx, osv.osv):
    """
    Define do_upload_po method to be called by stock move confirmation
    """
    
    _inherit = 'stock.picking'
    
    def do_upload_po(self, cr, uid, picking, context=None):
        """ 
        Called when the picking is assigned and has not yet been uploaded. 
        See stock move file for more info 
        """
        self.upload(cr, 1, picking, lx_purchase_order)
