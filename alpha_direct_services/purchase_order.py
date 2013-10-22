#!/usr/bin/python

from copy import copy
from openerp.osv import osv, fields
from ads_purchase_order import ads_purchase_order

def upload_po_picking(stock_picking_obj, cr, uid, picking_id, vals={}, context=None):
    """
    Extract and upload products from a pickings move_lines, then
    extract and upload the picking to the server.

    If there is an exception it will be saved to ads_result. Otherwise
    ads_sent will be set to True
    """
    try:
        picking = stock_picking_obj.browse(cr, uid, picking_id, context=context)
        if picking.ads_sent:
            return
    
        # upload products first
        for move in picking.move_lines:
            stock_picking_obj.pool.get('product.product').ads_upload(cr, uid, move.product_id.id, context=context)
    
        data = ads_purchase_order(picking)
        data.upload(cr, stock_picking_obj.pool.get('ads.connection'))
        
        vals['ads_sent'] = True
        vals['ads_result'] = ''
    except stock_picking_obj.pool.get('ads.connection').connect_exceptions as e:
        vals['ads_sent'] = False
        vals['ads_result'] = str(e)
    super(stock_picking, stock_picking_obj).write(cr, uid, picking_id, vals, context=context)

class stock_picking(osv.osv):
    """
    Inherit the stock.picking object to trigger upload of PO pickings
    """
    _inherit = 'stock.picking'

    def create(self, cr, uid, values, context=None):
        """
        Process PO picking to upload to ADS and mark as successful or not.

        If picking created with state 'assigned', upload to ADS. If successful,
        set ads_sent to True. Otherwise False, and save exception string in ads_result
        """
        picking_id = super(stock_picking, self).create(cr, uid, values, context=context)

        # is this a picking for the PO?
        if 'origin' in values and values['origin'][0:2] == 'PO' \
            and 'name' in values and values['name'][0:2] == 'IN':

            # if state is assigned, upload to ADS and set ads_sent and ads_result as appropriate
            if 'state' in values and values['state'] == 'assigned':
                upload_po_picking(self.pool, cr, uid, picking_id, context)
                return picking_id
            else:
                # otherwise return id like normal
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
        
        if not hasattr(ids, '__iter__'):
            ids = [ids]

        def check_state(values):
            """ Make sure we are changing the state to assigned """
            if 'state' in values and values['state'] == 'assigned':
                return True
            else:
                return False

        def check_type(obj, cr, ids):
            """ Make sure all pickings in the write have origin SO* """
            pickings = obj.browse(cr, 1, ids, context=context)
            return bool([picking for picking in pickings if picking.type.lower() == 'in'])

        # if state is assigned and origin is SO
        if check_state(values) and check_type(self, cr, ids):

            # for each target picking, upload and set results
            for picking_id in ids:
                upload_po_picking(self, cr, uid, picking_id, vals=copy(values), context=context)
            return True
        else:
            # otherwise return from write like normal
            return super(stock_picking, self).write(cr, uid, ids, values, context=context)

class stock_picking_in(osv.osv):

    _inherit = 'stock.picking.in'

    def create(self, cr, uid, values, context=None):
        return super(stock_picking_in, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        return super(stock_picking_in, self).write(cr, uid, ids, values, context=context)
