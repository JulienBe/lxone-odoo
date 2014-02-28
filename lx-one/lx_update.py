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
        'sequence': fields.char('Execution Sequence'),
        'state': fields.selection( (
                ('To Execute', 'to_execute'), 
                ('Executed', 'executed'), 
                ('Failed', 'failed')
            ), 'State'),
        'object_type': fields.char('Object Type', size=12),
        'data': fields.text('Data'),
        'result': fields.text('Execution Result'),
        'file_name': fields.char('File Name', size=64),
        'node_number': fields.integer('XML Node Number'),
    }

    _defaults = { 
        'sequence': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'lx.update')
    }

    def execute(self, cr, uid, ids, context=None):
        raise NotImplementedError("This method should execute this update's data")

    def execute_all(self, cr, uid, context=None):
        raise NotImplementedError("This method should search for all to_execute and failed updates and execute them")
