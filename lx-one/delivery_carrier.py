from openerp.osv import osv, fields

class delivery_carrier(osv.osv):
    """
    Inherit the stock.picking object to trigger upload of PO pickings
    """
    _inherit = 'delivery.carrier'
    _columns = {
        'lx_ref': fields.char('LX Ref', help="The corresponding reference number for LX1. This is the value that will be uploaded to LX1 with the picking", required=True)
    }
