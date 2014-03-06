from openerp.osv import osv, fields
import oe_lx

class delivery_carrier(oe_lx.oe_lx, osv.osv):
    """
    Inherit the stock.picking object to trigger upload of PO pickings
    """
    _name = 'delivery.carrier'
    _inherit = 'delivery.carrier'
    _columns = {
        'lx_ref': fields.char('LX Ref', help="The corresponding reference number for LX1. This is the value that will be uploaded to LX1 with the picking", required=True)
    }
