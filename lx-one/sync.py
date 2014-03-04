from openerp.osv import osv, fields
from openerp.tools.translate import _
from copy import deepcopy

class lx_sync(osv.osv):
    """
    A sync record is created each time the FTP server is polled and at least 1 importable file is found 
    """

    _name = 'lx.sync'
    _order = 'date DESC'
    
    _columns = {
        'date': fields.datetime('Sync Date', readonly=True),
        'update_file_ids': fields.one2many('lx.update.file', 'sync_id', 'Files', readonly=True),
        'log': fields.text('Sync Log', readonly=True),
    }
    
    def _sanitize_values(self, vals):
        """ Convert list of log messages to string with elements separated by new lines """
        vals = deepcopy(vals)
        if isinstance(vals.get('log', False), (list, tuple)):
            vals['log'] = '\n'.join(vals['log'])
        return vals
    
    def create(self, cr, uid, vals, context=None):
        """ Sanitize input values """
        vals = self._sanitize_values(vals)
        return super(lx_sync, self).create(cr, uid, vals, context=context)
        
    def write(self, cr, uid, ids, vals, context=None):
        """ Sanitize input values """
        vals = self._sanitize_values(vals)
        return super(lx_sync, self).write(cr, uid, ids, vals, context=context)
