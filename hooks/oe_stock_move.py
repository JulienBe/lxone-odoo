from openerp.osv import osv

class stock_move(osv.osv):
    """
    Inherit stock move action_assign and force_assign to trigger
    do_upload_po or do_upload_so according to picking type if 
    picking state is assigned.
    """

    _inherit = 'stock.move'

    def action_assign(self, cr, uid, ids, context=None):
        res = super(stock_move, self).action_assign(cr, uid, ids, context=context)
        self.do_upload(cr, uid, ids, context=context)
        return res

    def force_assign(self, cr, uid, ids, context=None):
        res = super(stock_move, self).force_assign(cr, uid, ids, context=context)
        self.do_upload(cr, uid, ids, context=context)
        return res
        
    def do_upload(self, cr, uid, ids, context=None):
        """ 
        check the type of the move's picking and call the appropriate do_upload_* method 
        if not hasn't yet been uploaded
        """
        for move in self.browse(cr, uid, ids, context=context):
            move.picking_id.refresh() # refresh picking because it is cached in the orm, causing lx_file_outgoing_ids to be empty after upload
            if move.picking_id and move.picking_id.state == 'assigned' and not move.picking_id.lx_file_outgoing_ids:
                if move.picking_id.picking_type_id.code == 'outgoing':
                    self.pool['stock.picking'].do_upload_so(cr, uid, move.picking_id, context=context)
                if move.picking_id.picking_type_id.code == 'incoming':
                    self.pool['stock.picking'].do_upload_po(cr, uid, move.picking_id, context=context)
        
class stock_picking(osv.osv):
    """
    Provide method stubs for do_upload_so and do_upload_po called by stock.move.do_upload 
    """

    _inherit = 'stock.picking'

    def do_upload_so(self, cr, uid, id, context=None):
        raise NotImplementedError()
    
    def do_upload_po(self, cr, uid, id, context=None):
        raise NotImplementedError()
