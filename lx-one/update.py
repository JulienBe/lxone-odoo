from openerp.osv import osv, fields
from openerp.tools.translate import _

class lx_update(osv.osv):
    """
    These records represent data coming from LX1. Each one should be able to be executed
    independently from the rest, i.e. the reception of a picking order or a physical inventory.

    They are designed to be created based on the data from XML files that are downloaded from 
    LX1's FTP server, and executed in the same order that they were created.
    """

    _name = 'lx.update'

    _columns = {
        'sequence': fields.char('Execution Sequence', required=True, readonly=True),
        'state': fields.selection( (
                ('to_execute', 'To Execute'), 
                ('executed', 'Executed'), 
                ('failed', 'Failed')
            ), 'State'),
        'object_type': fields.char('Object Type', size=12, required=True, readonly=True),
        'data': fields.text('Data', required=True,),
        'result': fields.text('Execution Result', readonly=True),
        'file_name': fields.char('File Name', size=64, required=True, readonly=True),
        'node_number': fields.integer('XML Node Number', required=True, readonly=True),
    }

    _defaults = { 
        'state': 'to_execute',
        'result': '',
        'sequence': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'lx.update')
    }

    def execute(self, cr, uid, ids, context=None):
        """
        Sorts IDs by their sequence, process them, then set state to executed
        """
        updates = self.read(cr, uid, ids, ['sequence'], context=context)
        updates.sort(key=lambda update: int(update['sequence']))
        for update in updates:
            update = self.browse(cr, uid, update['id'], context=context)
            
            # do importation
            try:
                result = 'Picking closed'
            
                # change state
                update.write({'state': 'executed', 'result': result})
            except Exception, e:
                result = 'Error while executing: %s' % str(e)
                update.write({'state': 'failed', 'result': result})

    def execute_all(self, cr, uid, ids=[], context=None):
        """ Gets ids for all updates whose state is not imported and calls execute on them """
        all_ids = self.search(cr, uid, [('state', '!=', 'imported')], context=context)
        self.execute(cr, uid, all_ids)
