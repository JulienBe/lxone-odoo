from copy import copy

from openerp.tools.translate import _
from openerp.osv import osv, fields

def all_assigned(picking_obj, cr, ids):
    for picking in picking_obj.read(cr, 1, ids, ['state']):
        if picking['state'] != 'assigned':
            return False
    return True

class stock_picking(osv.osv):
    """ Inherit the stock.picking to prevent manual processing and cancellation after ads upload """

    _inherit = 'stock.picking'

    def action_process(self, cr, uid, ids, context=None):
        if all_assigned(self, cr, ids):
            raise osv.except_osv(_('Cannot Process Manually'), _("The picking should be processed in the ADS system. It will then be automatically synchronized to OpenERP."))
        else:
            super(stock_picking, self).action_process(cr, uid, ids, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        if all_assigned(self, cr, ids):
            raise osv.except_osv(_('Cannot Cancel'), _("You can't cancel a picking when it is in 'Ready to Receive' state because it has already been sent to ADS.") )
        else:
            super(stock_picking, self).action_cancel(cr, uid, ids, context=context)

class stock_picking_in(osv.osv):
    """ Inherit the stock.picking.in to prevent manual processing and cancellation after ads upload """

    _inherit = 'stock.picking.in'

    def action_process(self, cr, uid, ids, context=None):
        if all_assigned(self, cr, ids):
            raise osv.except_osv(_('Cannot Receive Manually'), _("The picking should be received in the ADS system. It will then be automatically synchronized to OpenERP."))
        else:
            super(stock_picking_in, self).action_process(cr, uid, ids, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        if all_assigned(self, cr, ids):
            raise osv.except_osv(_('Cannot Cancel'), _("You can't cancel a picking when it is in 'Ready to Receive' state because it has already been sent to ADS.") )
        else:
            super(stock_picking_in, self).action_cancel(cr, uid, ids, context=context)

class stock_picking_out(osv.osv):
    """ Inherit the stock.picking.in to prevent manual processing and cancellation after ads upload """

    _inherit = 'stock.picking.out'

    def action_process(self, cr, uid, ids, context=None):
        if all_assigned(self, cr, ids):
            raise osv.except_osv(_('Cannot Deliver Manually'), _("The picking should be marked as delivered in the ADS system. It will then be automatically synchronized to OpenERP."))
        else:
            super(stock_picking_out, self).action_process(cr, uid, ids, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        if all_assigned(self, cr, ids):
            raise osv.except_osv(_('Cannot Cancel'), _("You can't cancel a picking when it is in 'Ready to Receive' state because it has already been sent to ADS.") )
        else:
            super(stock_picking_out, self).action_cancel(cr, uid, ids, context=context)
