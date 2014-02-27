import logging
_logger = logging.getLogger(__name__)

from openerp.osv import osv,fields
from ads_product import ads_product

class product_product(osv.osv):
    """
    Add some fields to product to track synchronisation and trigger upload on write
    """
    _inherit = 'product.product'
    _columns = {
        'discount': fields.boolean('Discount', help="This product is used to add discounts to orders by giving a negative quantity")
    }

    def write(self, cr, uid, ids, values, context=None):
        """ Call ads_upload if we edit an uploaded field """
        res = super(product_product, self).write(cr, uid, ids, values, context=context)
        if any([field for field in ads_product.uploaded_fields if field in values.keys()]):
            self.ads_upload(cr, uid, ids, context=context)
        return res
    
    def create(self, cr, uid, values, context=None):
        """ Call ads_upload """
        res = super(product_product, self).create(cr, uid, values, context=context)
        self.ads_upload(cr, uid, res, context=context)
        return res

    def ads_upload_all(self, cr, uid, context=None):
        ids = self.search(cr, uid, [('x_new_ref', '!=', '')])
        _logger.info("Starting upload of %d products" % len(ids))
        self.ads_upload(cr, uid, ids, log=True, context=context)
        return True

    def ads_upload(self, cr, uid, ids, log=False, context=None):
        """ Upload product to ads server """
        if not isinstance(ids, (list, tuple)):
            ids = [ids]

        for product_id in ids:
            product = self.browse(cr, uid, product_id, context=context)
            if not product.x_new_ref:
                continue
            data = ads_product(product)
            data.upload(cr, self.pool.get('ads.manager'))
            if log:
                _logger.info("Uploaded product with ID %d" % product_id)
        return True
    
    def is_delivery_method(self, cr, uid, ids, context=None):
        """
        Returns a dictionary of product IDS, where each id maps to a list of carrier ids, or False
        if none were found
        """
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
            
        is_delivery_map = dict.fromkeys(ids, False)
        carrier_obj = self.pool['delivery.carrier']
        
        for product_id in ids:
            delivery_method_ids = carrier_obj.search(cr, uid, [('product_id','=',product_id)])
            
            if delivery_method_ids:
                is_delivery_map[product_id] = delivery_method_ids
        
        return is_delivery_map
