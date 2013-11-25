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
                
                # Behave differently if it is a partial or not. If it is a partial,
                # there will be more than 1 picking in confirmed or assigned state.
                pickings_for_so = self.search(cr, uid, [
                    ('sale_id','=',picking.sale_id.id),
                    ('type','=','out'),
                    ('state','not in',['cancel', 'done'])]
                )
                if len(pickings_for_so) == 1:
                    ## First BL or CREX ##
                    upload_so_picking(self, cr, uid, picking_id, context=context)
                else:
                    ## Partial / Return ##
                    returns = [p for p in self.browse(cr, 1, pickings_for_so) if '-ret' in p.name and not p.ads_sent]
                    if returns:
                        # found un-uploaded return, so upload it
                        for ret in returns:
                            picking_id = ret.id
                            all_pickings_for_so = self.search(cr, 1, [('origin','=',picking.origin)])
                            send_number = sorted([p.ads_send_number for p in self.browse(cr, 1, all_pickings_for_so)], reverse=True)[0] + 1
                            self.write(cr, 1, picking_id, {'ads_send_number': send_number})
                            upload_so_picking(self, cr, uid, picking_id, context=context)
                    else:
                        # Otherwise, find partial with unprocessed lines, add ads_send_number, then upload
                        picking_id = sorted(set(pickings_for_so) - set(ids))[0]
                        all_pickings_for_so = self.search(cr, 1, [('origin','=',picking.origin)])
                        send_number = sorted([p.ads_send_number for p in self.browse(cr, 1, all_pickings_for_so)], reverse=True)[0] + 1
                        self.write(cr, 1, picking_id, {'ads_send_number': send_number})
                        upload_so_picking(self, cr, uid, picking_id, context=context)

        return res
    
    def copy(self, cr, uid, id, default=None, context=None):
        """ Set ads_sent back to False - caused by duplication during action_process of partial wizard """
        res = super(stock_picking, self).copy(cr, uid, id, default=default, context=context)
        self.write(cr, uid, res, {'ads_sent': False})
        return res
