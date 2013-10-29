from copy import copy
from openerp.osv import osv
from ads_sales_order import ads_sales_order

def upload_so_picking(stock_picking_obj, cr, uid, picking_id, vals={}, context=None):
    """
    Extract and upload the picking to the server.
    If there is an exception it will be raised.
    """
    picking = stock_picking_obj.browse(cr, uid, picking_id, context=context)
    data = ads_sales_order(picking)
    data.upload(cr, stock_picking_obj.pool.get('ads.manager'))

class stock_picking(osv.osv):
    """
    Inherit the stock.picking object to trigger upload of SO pickings
    """
    _inherit = 'stock.picking'

    def create(self, cr, uid, values, context=None):
        """
        Create SO picking and upload to ADS if state is assigned.
        """
        picking_id = super(stock_picking, self).create(cr, uid, values, context=context)

        # is this a picking for the SO?
        if 'origin' in values and values['origin'][0:2] == 'SO' \
            and 'name' in values and values['name'][0:3] == 'OUT':

            # if state is assigned, upload to ADS 
            if 'state' in values and values['state'] == 'assigned':
                upload_so_picking(self, cr, uid, picking_id, context=context)
                return picking_id
            else:
                # otherwise return id like normal
                return picking_id
        else:
            return picking_id

    def write(self, cr, uid, ids, values, context=None):
        """
        If picking state is changed to assigned, upload to ADS
        """

        if not hasattr(ids, '__iter__'):
            ids = [ids]

        def check_state(values):
            """ Make sure we are changing the state to assigned """
            if 'state' in values and values['state'] == 'assigned':
                return True
            else:
                return False

        def check_type(obj, cr, picking_id):
            """ Make sure all pickings in the write have origin SO* """
            picking = obj.browse(cr, 1, picking_id, context=context)
            return picking.type.lower() == 'out'

        # perform the write and save value to return later
        res = super(stock_picking, self).write(cr, uid, ids, values, context=context)

        # are we changing the state to assigned?
        if not check_state(values):
            return res

        # check type of each picking and upload if appropriate
        for picking_id in ids:
            if check_type(self, cr, picking_id):
                upload_so_picking(self, cr, uid, picking_id, vals=copy(values), context=context)

        # return result of write
        return res

class stock_picking_in(osv.osv):

    _inherit = 'stock.picking.in'

    def create(self, cr, uid, values, context=None):
        return super(stock_picking_in, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        return super(stock_picking_in, self).write(cr, uid, ids, values, context=context)
