#!/usr/bin/python

from copy import copy
from openerp.osv import osv, fields
from ads_sales_order import ads_sales_order

def upload_so_picking(pool, cr, uid, picking_id, context=None):
    """
    Extract a picking into an ads_sales_order then upload to server.
    Any exceptions will be raised to the level above. If no exceptions, it
    can be assumed that the process was successful. If the picking
    is already marked as ads_sent it will be ignored and this method will
    return None.
    """
    picking = pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
    if picking.ads_sent:
        return
    
    data = ads_sales_order()
    data.extract_picking_in(picking)
    pool.get('ads.connection').connect(cr).upload_data(data)

class stock_picking(osv.osv):
    """
    Inherit the stock.picking object to trigger upload of SO pickings 
    """
    _inherit = 'stock.picking'
    
    def create(self, cr, uid, values, context=None):
        """
        Process SO picking to upload to ADS and mark as successful or not.
        """
        picking_id = super(stock_picking, self).create(cr, uid, values, context=context)

        if 'origin' in values and values['origin'][0:2] == 'SO' \
            and 'name' in values and values['name'][0:3] == 'OUT':
            
            print 'TODO: upload SO picking'
            return picking_id
            
        else:
            return picking_id

    def write(self, cr, uid, ids, values, context=None):
        """
        On write, if state is changed to 'assigned', create a document
        containing the data for the IN and upload it to the ADS server.
        If the upload is successful, set ads_sent to true. Otherwise
        set it to false and save the exception message in ads_result.
        """
        return super(stock_picking, self).write(cr, uid, ids, values, context=context)

class stock_picking_in(osv.osv):

    _inherit = 'stock.picking.in'
    
    def create(self, cr, uid, values, context=None):
        return super(stock_picking_in, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        return super(stock_picking_in, self).write(cr, uid, ids, values, context=context)
