from copy import copy
from openerp.osv import osv, fields
from ads_purchase_order import ads_purchase_order

def upload_po_picking(stock_picking_obj, cr, uid, picking_id, vals={}, context=None):
    """
    Extract and upload the picking to the server.
    If there is an exception it will be raised.
    """
    picking = stock_picking_obj.browse(cr, uid, picking_id, context=context)
    data = ads_purchase_order(picking)
    data.upload(cr, stock_picking_obj.pool.get('ads.manager'))
    stock_picking_obj.write(cr, uid, picking_id, {'ads_sent': True})

class stock_picking(osv.osv):
    """
    Inherit the stock.picking object to trigger upload of PO pickings
    """
    _inherit = 'stock.picking'

    def create(self, cr, uid, values, context=None):
        """
        Create PO picking and upload to ADS if state is assigned.
        """
        picking_id = super(stock_picking, self).create(cr, uid, values, context=context)

        # is this a picking for the PO?
        if 'origin' in values and values['origin'][0:2] == 'PO' \
            and 'name' in values and values['name'][0:2] == 'IN':

            # if state is assigned, upload to ADS 
            if 'state' in values and values['state'] == 'assigned':
                upload_po_picking(self, cr, uid, picking_id, context=context)
                return picking_id
            else:
                # otherwise return id like normal
                return picking_id
        else:
            return picking_id

    def write(self, cr, uid, ids, values, context=None):
        """
        If pick state is changed to assigned, upload to ADS
        """
        if not hasattr(ids, '__iter__'):
            ids = [ids]

        def state_correct(values):
            """ Make sure we are changing the state to assigned """
            return 'state' in values and values['state'] == 'assigned' or False

        def type_correct(obj, cr, pick):
            """ Make sure all pickings in the write have origin SO* """
            return pick.type == 'in'
        
        def is_sent(obj, cr, pick):
            return pick.ads_sent
        
        def others_exist(obj, cr, pick):
            return len(self.search(cr, uid, [('origin','=',pick.origin),('type','=','in')])) > 1 

        # perform the write and save value to return later
        res = super(stock_picking, self).write(cr, uid, ids, values, context=context)
        
        if 'ads_sent' in values:
            return res
        
        # are we changing the state to assigned?
        if not state_correct(values):
            return res

        # check type of each pick and upload if appropriate
        for picking_id in ids:
            pick = self.browse(cr, 1, picking_id, context=context)
            if type_correct(self,cr,pick) and not is_sent(self,cr,pick) and not others_exist(self,cr,pick): 
                upload_po_picking(self, cr, uid, picking_id, vals=copy(values), context=context)

        # return result of write
        return res

class stock_picking_in(osv.osv):

    _inherit = 'stock.picking.in'

    def create(self, cr, uid, values, context=None):
        return super(stock_picking_in, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        return super(stock_picking_in, self).write(cr, uid, ids, values, context=context)
