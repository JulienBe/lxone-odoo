from copy import copy

from openerp.osv import osv,fields

from lx_sales_order import lx_sales_order
from oe_lx import oe_lx

def upload_so_picking(stock_picking_obj, cr, uid, picking_id, context=None):
    """
    Extract and upload the picking to the server. If upload returns False, it means
    there were no deliverable BL lines and it should be automatically marked delivered.
    If there is an exception it will be raised.
    """
    picking = stock_picking_obj.browse(cr, uid, picking_id, context=context)
    data = lx_sales_order(picking)

    if not data.upload(cr, stock_picking_obj.pool.get('lx.manager')):
        # no lines in BL, so it consists only of undeliverable lines. Mark as delivered
        wizard_obj = stock_picking_obj.pool['stock.partial.picking']
        context = {
            'active_model': 'stock.picking.out',
            'active_ids': [picking_id],
            'active_id': picking_id,
        }
        wizard_id = wizard_obj.create(cr, 1, {}, context=context)
        wizard_obj.do_partial(cr, 1, [wizard_id])

    cr.commit()

class stock_picking(oe_lx, osv.osv):
    """
    Inherit the stock.picking object to trigger upload of SO pickings
    """
    _inherit = 'stock.picking'

    def action_assign_wkf(self, cr, uid, ids, context=None):
        """ Upload picking to LX1 """

        if not hasattr(ids, '__iter__'):
            ids = [ids]

        for picking_id in ids:
            picking = self.browse(cr, uid, picking_id, context=context)
            picking_to_upload = False

            if picking.type.lower() == 'out' and not picking.lx_sent:

                # find other delivery orders for this SO in assigned state
                partial_ids = self.search(cr, 1, [('sale_id','=',picking.sale_id.id),
                                                ('type','=','out'),
                                                ('state','in',['assigned','confirmed'])])

                if picking_id in partial_ids:
                    partial_ids.remove(picking_id)

                # Picking is a return, so simply upload it regardless of partials
                if 'ret' in picking.name:
                    picking_to_upload = picking_id

                # It's a normal non-partial picking, so upload it
                elif not partial_ids:
                    picking_to_upload = picking_id

                # It's a partial, so it's the other picking that we are interested in.
                # Set lx_sent to False and upload if state is assigned. Otherwise wait for scheduler
                else:
                    partial_id = sorted(partial_ids)[0]
                    self.write(cr, uid, partial_id, {'lx_sent': False})
                    picking = self.browse(cr, 1, partial_id)

                    if picking.state == 'assigned':
                        picking_to_upload = partial_id

                # Finally, upload the picking if applicable
                if picking_to_upload:
                    all_pickings_for_so = self.search(cr, 1, [('sale_id', '=', picking.sale_id.id)])
                    send_number = sorted([p.lx_send_number for p in self.browse(cr, 1, all_pickings_for_so)], reverse=True)[0] + 1

                    self.write(cr, 1, picking_to_upload, {'lx_send_number': send_number})
                    upload_so_picking(self, cr, uid, picking_to_upload, context=context)

            super(stock_picking, self).action_assign_wkf(cr, uid, picking_id, context=context)
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        """ Set lx_sent back to False - caused by duplication during action_process of partial wizard """
        res = super(stock_picking, self).copy(cr, uid, id, default=default, context=context)
        self.write(cr, uid, res, {'lx_sent': False, 'lx_file_name': ''})
        return res

