import logging
_logger = logging.getLogger(__name__)

from openerp.osv import osv,fields
from lx_product import lx_product
from oe_lx import oe_lx

def lx_upload(self, cr, uid, ids, log=False, context=None):
    """ Upload products with ids. If log is True, will write a log line for  each uploaded product """
    uploaded_file_names = []
    for product in self.browse(cr, uid, ids):
        uploaded_file_names.append(self.upload(cr, uid, product, lx_product))
        if log:
            _logger.info("Uploaded product with id %d" % product.id)
    return uploaded_file_names

def lx_upload_all(self, cr, uid, ids=[], context=None):
    """ Upload ALL products. Will write a log for each product """
    ids = self.search(cr, uid, [])
    _logger.info("Starting upload of %d products" % len(ids))
    return self.lx_upload_one(cr, uid, self.browse(cr, uid, ids, context=context), log=True, context=context)

def is_delivery_method(self, cr, uid, ids, context=None):
    """
    Returns a dictionary of product IDS, where each id maps to a list of carrier ids, or False
    if none were found:
    
    {23: [1,5], 29: False}
    """
    if not isinstance(ids, (list, tuple)):
        ids = [ids]
        
    is_delivery_map = dict.fromkeys(ids, False)
    carrier_obj = self.pool['delivery.carrier']
    
    for product_id in ids:
        delivery_method_ids = carrier_obj.search(cr, 1, [('product_id','=',product_id)])
        
        if delivery_method_ids:
            is_delivery_map[product_id] = delivery_method_ids
    
    return is_delivery_map

class product_template(oe_lx, osv.osv):
    """
    Trigger upload on create, and on write if fields we are interested in have been touched
    Also provide upload all functionality, and helper method to determine if product is a delivery product
    """
    _inherit = 'product.template'

    def write(self, cr, uid, ids, values, context=None):
        """ Call lx_upload if we edit an uploaded field """
        res = super(product_template, self).write(cr, uid, ids, values, context=context)
        if any([field for field in lx_product.required_fields if field in values.keys()]):
            lx_upload(self, cr, 1, ids, context=context)
        return res
    
    def create(self, cr, uid, values, context=None):
        """ Call lx_upload """
        res = super(product_template, self).create(cr, uid, values, context=context)
        lx_upload(self, cr, 1, [res], context=context)
        return res
    
class product_product(oe_lx, osv.osv):
    """
    Trigger upload on create, and on write if fields we are interested in have been touched
    Also provide upload all functionality, and helper method to determine if product is a delivery product
    """
    _inherit = 'product.product'

    def write(self, cr, uid, ids, values, context=None):
        """ Call lx_upload if we edit an uploaded field """
        res = super(product_product, self).write(cr, uid, ids, values, context=context)
        if any([field for field in lx_product.required_fields if field in values.keys()]):
            lx_upload(self, cr, 1, ids, context=context)
        return res
    
    def create(self, cr, uid, values, context=None):
        """ Call lx_upload """
        res = super(product_product, self).create(cr, uid, values, context=context)
        lx_upload(self, cr, 1, [res], context=context)
        return res
