from openerp.osv import osv, fields

class product_uom(osv.osv):
    """
    Add corresponding reference for LX1
    """
    _inherit = 'product.uom'
    
    _columns = {
        'lx_ref': fields.char('LX Reference', help="The corresponding reference number for LX1. This is the value that will be uploaded to LX1 with the picking", required=True)
    }
