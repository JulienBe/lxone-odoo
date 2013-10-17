#!/usr/bin/python

from copy import copy
from openerp.osv import osv, fields
from ads_purchase_order import ads_purchase_order

def upload_po_picking(pool, cr, uid, picking_id, context=None):
    """
    Extract a picking into an ads_purchase_order then upload to server.
    Any exceptions will be raised to the level above. If no exceptions, it
    can be assumed that the process was successful. If the picking
    is already marked as ads_sent it will be ignored and this method will
    return None.
    """
    picking = pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
    if picking.ads_sent:
        return
    
    data = ads_purchase_order()
    data.extract_picking_in(picking)
    pool.get('ads.connection').connect(cr).upload_data(data)

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
                vals = {}
                try:
                    self._ads_process(cr, uid, picking_id, context)
                    vals['ads_sent'] = True
                except Exception, e:
                    vals['ads_sent'] = False
                    vals['ads_result'] = str(e)
                super(stock_picking, self).write(cr, uid, picking_id, vals, context=context)
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
        # if state is assigned, for each target picking, upload and set results
        if 'state' in values and values['state'] == 'assigned':
            for picking_id in ids:
                vals = copy(values)
                try:
                    upload_po_picking(self.pool, cr, uid, picking_id, context=context)
                    vals['ads_sent'] = True
                except Exception, e:
                    vals['ads_sent'] = False
                    vals['ads_result'] = str(e)
                super(stock_picking, self).write(cr, uid, picking_id, vals, context=context)
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
