from openerp.osv import osv, fields
from ads_product import ads_product
from ads_tools import parse_date

from datetime import datetime
import time

class product_product(osv.osv):
    """
    Add some fields to product to track synchronisation
    """
    _inherit = 'product.product'
    _columns = {
        'ads_sent': fields.boolean('Sent to ADS?'),
        'ads_sent_date': fields.datetime('ADS Sent Date', help="The date at which this product was sent to ADS. If blank it has never been sent"),
        'ads_result': fields.text('Results of send to ADS'),
        'ads_last_modified': fields.datetime('The date this object was last modified'),
    }

    def write(self, cr, uid, ids, values, context=None):
        """ Keep track of when products are modified so they can be re-uploaded """
        if not [field for field in ['ads_result', 'ads_sent', 'ads_sent_date'] if field in values]:
            values['ads_last_modified'] =  time.strftime("%Y-%m-%d %H:%M:%S")
        return super(product_product, self).write(cr, uid, ids, values, context=context)

    def ads_upload(self, cr, uid, ids, context=None):
        """ Upload product if ads_sent is false, or ads_sent_date < datetime.now() """
        if not isinstance(ids, (list, tuple)):
            ids = [ids]

        def need_to_upload(product):
            """
            Returns True if we need to upload the product because it has not yet
            been uploaded or has been modified since the last upload
            """
            if product.ads_sent:
                if product.ads_sent_date and product.ads_last_modified:
                    if parse_date(product.ads_sent_date) < parse_date(product.ads_last_modified):
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return True

        for product_id in ids:
            product = self.browse(cr, uid, product_id, context=context)
            if need_to_upload(product):
                try:
                    data = ads_product(product)
                    data.upload(cr, self.pool.get('ads.connection'))
                    self.write(cr, uid, product_id, {'ads_sent': True, 'ads_sent_date': time.strftime("%Y-%m-%d %H:%M:%S"), 'ads_result': ''})
                except self.pool.get('ads.connection').connect_exceptions as e:
                    self.write(cr, uid, product_id, {'ads_sent_date': False, 'ads_result': str(e)})
                    raise e
