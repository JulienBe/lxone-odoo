import logging
_logger = logging.getLogger(__name__)

from openerp.osv import osv,fields
from lx_product import lx_product
import oe_lx 

class product_product(oe_lx.oe_lx, osv.osv):
    """
    Add some fields to product to track synchronisation and trigger upload on write
    """
    _inherit = 'product.product'

    def write(self, cr, uid, ids, values, context=None):
        """ Call lx_upload if we edit an uploaded field """
        res = super(product_product, self).write(cr, uid, ids, values, context=context)
        if any([field for field in lx_product.uploaded_fields if field in values.keys()]):
            self.lx_upload(cr, uid, ids, context=context)
        return res
    
    def create(self, cr, uid, values, context=None):
        """ Call lx_upload """
        res = super(product_product, self).create(cr, uid, values, context=context)
        self.lx_upload(cr, uid, res, context=context)
        return res

    def lx_upload_all(self, cr, uid, context=None):
        ids = self.search(cr, uid, [('x_new_ref', '!=', '')])
        _logger.info("Starting upload of %d products" % len(ids))
        self.lx_upload(cr, uid, ids, log=True, context=context)
        return True

    def lx_upload(self, cr, uid, ids, log=False, context=None):
        """ Upload product to LX1 server """
        if not isinstance(ids, (list, tuple)):
            ids = [ids]

        for product_id in ids:
            product = self.browse(cr, uid, product_id, context=context)
            if not product.x_new_ref:
                continue
            data = lx_product(product)
            data.upload(cr, self.pool.get('lx.manager'))
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
