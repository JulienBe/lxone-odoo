from copy import copy
from openerp.osv import osv, fields
from ads_sales_order import ads_sales_order

def upload_so_picking(stock_picking_obj, cr, uid, picking_id, vals={}, context=None):
    """
    Extract and upload the picking to the server.
    If there is an exception it will be raised.
    """
    picking = stock_picking_obj.browse(cr, uid, picking_id, context=context)
    data = ads_sales_order(picking)
    data.upload(cr, stock_picking_obj.pool.get('ads.manager'))
    stock_picking_obj.write(cr, uid, picking_id, {'ads_sent': True})

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

        # perform the write and save value to return later
        res = super(stock_picking, self).write(cr, uid, ids, values, context=context)
        if 'ads_sent' in values:
            return res
        
        for picking_id in ids:
            picking = self.browse(cr, uid, picking_id, context=context)
            
            state_correct = picking.state == 'assigned' or 'state' in values and values['state'] == 'assigned' or False
            type_correct = picking.type.lower() == 'out'

            if state_correct and type_correct and not picking.ads_sent:
                # see if other outs with the same origin exist. If yes, upload the oldest because that is the one with the leftover lines
                pickings_for_so = self.search(cr, uid, [('origin','=',picking.origin),('type','=','out')])
                if len(pickings_for_so) > 1:
                    picking_id = sorted(list(set(pickings_for_so) - set(ids)))[0]
                
                upload_so_picking(self, cr, uid, picking_id, vals=copy(values), context=context)
                self.write(cr, uid, pickings_for_so, {'ads_sent': True})

        return res
    
    def copy(self, cr, uid, id, default=None, context=None):
        """ Set ads_sent back to False - caused by duplication during action_process of partial wizard """
        res = super(stock_picking, self).copy(cr, uid, id, default=default, context=context)
        self.write(cr, uid, res, {'ads_sent': False})
        return res

class stock_picking_in(osv.osv):

    _inherit = 'stock.picking.in'

    def create(self, cr, uid, values, context=None):
        return super(stock_picking_in, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        return super(stock_picking_in, self).write(cr, uid, ids, values, context=context)
