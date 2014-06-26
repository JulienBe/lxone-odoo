from openerp.osv import osv, fields

class delivery_carrier(osv.osv):
    """
    Add an lx reference field to delivery carriers to hold the reference to this 
    delivery option that resides in the LX One system
    """
    _inherit = 'delivery.carrier'
    
    _columns = {
        'lx_ref': fields.char('LX Reference', help="The corresponding reference number for LX1. This is the value that will be uploaded to LX1 with the picking", required=True)
    }
