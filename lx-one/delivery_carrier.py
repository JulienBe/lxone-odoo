from openerp.osv import osv, fields

class delivery_carrier(osv.osv):
    """
    Inherit the stock.picking object to trigger upload of PO pickings
    """
    _inherit = 'delivery.carrier'
    _columns = {
        'ads_ref': fields.char('ADS Ref', help="The corresponding reference number for ADS. This is the value that will be uploaded to ADS with the picking", required=True)
    }
