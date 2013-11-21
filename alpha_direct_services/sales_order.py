from copy import copy
from openerp.osv import osv, fields
from ads_sales_order import ads_sales_order

def upload_so_picking(stock_picking_obj, cr, uid, picking_id, context=None):
    """
    Extract and upload the picking to the server.
    If there is an exception it will be raised.
    """
    picking = stock_picking_obj.browse(cr, uid, picking_id, context=context)
    data = ads_sales_order(picking)
    data.upload(cr, stock_picking_obj.pool.get('ads.manager'))
    stock_picking_obj.write(cr, uid, picking_id, {'ads_sent': True})
    cr.commit()

class stock_picking(osv.osv):
    """
    Inherit the stock.picking object to trigger upload of SO pickings
    """
    _inherit = 'stock.picking'
    
    def action_assign_wkf(self, cr, uid, ids, context=None):
        """ Upload picking to ADS """
        
        if not hasattr(ids, '__iter__'):
            ids = [ids]

        res = super(stock_picking, self).action_assign_wkf(cr, uid, ids, context=context)
    
        for picking_id in ids:
            picking = self.browse(cr, uid, picking_id, context=context)

            if picking.type.lower() == 'out' and not picking.ads_sent:
                # Only upload the picking if there is only 1 open OUT found (Original, or 
                # CREX cancellation case).
                # In case of a partial there will be a second open OUT with the same origin.
                pickings_for_so = self.search(cr, uid, [
                    ('origin','=',picking.origin),
                    ('type','=','out'),
                    ('state','not in',['cancel', 'done'])]
                )
                if len(pickings_for_so) == 1:
                    upload_so_picking(self, cr, uid, picking_id, context=context)

        return res
    
    def copy(self, cr, uid, id, default=None, context=None):
        """ Set ads_sent back to False - caused by duplication during action_process of partial wizard """
        res = super(stock_picking, self).copy(cr, uid, id, default=default, context=context)
        self.write(cr, uid, res, {'ads_sent': False})
        return res
