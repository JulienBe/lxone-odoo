import ftplib
from ftplib import error_perm

from openerp.tools.translate import _
from openerp.osv import osv, fields

from ads_sales_order import ads_sales_order
from ads_purchase_order import ads_purchase_order

def all_assigned(picking_obj, cr, ids):
    for picking in picking_obj.read(cr, 1, ids, ['state']):
        if picking['state'] != 'assigned':
            return False
    return True

class stock_picking(osv.osv):
    """
    Inherit the stock.picking to prevent manual processing and cancellation after ads upload

    If ADS does not have stock to fulfill an order, they cancel the order and we have to re-upload
    it with a different BL and SO number. To handle this we cancel the BL, duplicate it (incrementing
    the name automatically) then append the value of the ads_send_number field to the end of the original
    SO name.
    """

    _inherit = 'stock.picking'
    _columns = {
        'ads_sent': fields.boolean('Sent to ADS?'),
        'ads_send_number': fields.integer('Send Number', help="Number of times this picking has been sent to ADS - used to re-send cancelled orders"),
        'ads_file_name': fields.char('Sent to ADS?', size=40, help="The name of the file uploaded to ADS"),
    }

    def action_process(self, cr, uid, ids, context=None):
        if all_assigned(self, cr, ids):
            raise osv.except_osv(_('Cannot Process Manually'), _("The picking should be processed in the ADS system. It will then be automatically synchronized to OpenERP."))
        else:
            super(stock_picking, self).action_process(cr, uid, ids, context=context)
            
    def action_cancel(self, cr, uid, ids, context=None):
        """ If file still exists on the server, delete it and cancel the picking. Otherwise raise an error """
        
        def cannot_cancel():
            raise osv.except_osv(_("Cannot Cancel Delivery Order"), _("The delivery order has already been imported by ADS so it cannot be canceled anymore"))
        
        for picking_id in ids:
            picking = self.browse(cr, uid, picking_id)
            if picking.ads_file_name:
                with self.pool['ads.manager'].connection(cr) as conn:
                    try:
                        conn.delete_data(picking.ads_file_name)
                        super(stock_picking, self).action_cancel(cr, uid, [picking_id], context=context)
                    except error_perm, e:
                        cannot_cancel()
            else:
                cannot_cancel()
        return True

class stock_picking_in(osv.osv):
    """ Inherit the stock.picking.in to prevent manual processing and cancellation after ads upload """

    _inherit = 'stock.picking.in'
    _columns = {
        'ads_send_number': fields.integer('Send Number', help="Number of times this picking has been sent to ADS - used to re-send cancelled orders"),
    }

    def action_disallow_invoicing(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'invoice_state': 'none'})

    def ads_manuel_upload(self, cr, uid, ids, context=None):
        """ Upload this picking to ADS """
        for picking_id in ids:
            picking = self.browse(cr, uid, picking_id, context=context)

            # make sure state is correct
            if not picking.state == 'assigned':
                continue

            data = ads_purchase_order(picking)
            data.upload(cr, self.pool.get('ads.manager'))
        return True


class stock_picking_out(osv.osv):
    """ Inherit the stock.picking.in to prevent manual processing and cancellation after ads upload """

    _inherit = 'stock.picking.out'

    def ads_manuel_upload(self, cr, uid, ids, context=None):
        """ Upload this picking to ADS """
        for picking_id in ids:
            picking = self.browse(cr, uid, picking_id, context=context)

            # make sure state is correct
            if not picking.state == 'assigned':
                continue

            data = ads_sales_order(picking)
            data.upload(cr, self.pool.get('ads.manager'))
        return True
