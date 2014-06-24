import logging
_logger = logging.getLogger(__name__)

from openerp.osv import osv,fields
from lx_product import lx_product
from oe_lx import oe_lx

class product_super(object):
    """ Defines some methods common to product.template and product.product """
    
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

class product_template(oe_lx, product_super, osv.osv):
    """
    Trigger upload on create, and on write if fields we are interested in have been touched
    Also provide upload all functionality, and helper method to determine if product is a delivery product
    """
    _inherit = 'product.template'
    
    def write(self, cr, uid, ids, values, context=None):
        """ Call product_upload if we edit an uploaded field """
        res = super(product_template, self).write(cr, uid, ids, values, context=context)
        
        if 'name' in values and 'ean13' not in values:
            _logger.info("%s UPLOADING VARIENTS" % self._name)
            records_to_upload = []
            for record in self.browse(cr, uid, ids, context=context):
                records_to_upload = records_to_upload + [var.id for var in record.product_variant_ids]
            self.pool['product.product'].product_upload(cr, uid, records_to_upload, context=context)
        
        return res
    
    def create(self, cr, uid, values, context=None):
        """ Call product_upload """
        res = super(product_template, self).create(cr, uid, values, context=context)
        lx_upload(self, cr, 1, [res], context=context)
        return res
    
class product_product(oe_lx, product_super, osv.osv):
    """
    Trigger upload on create, and on write if fields we are interested in have been touched
    Also provide upload all functionality, and helper method to determine if product is a delivery product
    """
    _inherit = 'product.product'

    def product_upload(self, cr, uid, ids, context=None):
        """ Upload products with ids """
        if not hasattr(ids, '__iter__'):
            ids = [ids]
            
        products = self.browse(cr, uid, ids)
        self.upload(cr, uid, products, lx_product)
        return True
    
    def product_upload_all(self, cr, uid, context=None):
        """ Upload ALL products. Will write a log for each product """
        ids = self.search(cr, uid, [('type','=','product')])
        return self.product_upload(cr, uid, ids)
    
    def write(self, cr, uid, ids, values, context=None):
        """ Call product_upload if we edit an uploaded field """
        res = super(product_product, self).write(cr, uid, ids, values, context=context)
        
        if 'ean13' in values or 'name' in values:
            _logger.info("%s UPLOADING" % self._name)
            self.product_upload(cr, 1, ids, context=context)
        return res
    
    def create(self, cr, uid, values, context=None):
        """ Call product_upload """
        res = super(product_product, self).create(cr, uid, values, context=context)
        lx_upload(self, cr, 1, [res], context=context)
        return res
