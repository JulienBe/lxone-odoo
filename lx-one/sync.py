from openerp.osv import osv, fields
from openerp.tools.translate import _
from copy import deepcopy

class lx_sync(osv.osv):
    """
    A sync record is created each time the FTP server is polled and at least 1 importable file is found 
    """

    _name = 'lx.sync'
    _order = 'date DESC'
    
    def _get_file_count(self, cr, uid, ids, field_name, arg, context):
        res = dict.fromkeys(ids)
        for node in self.browse(cr, uid, ids, context=context):
            res[node.id] = len(node.update_file_ids)
        return res
    
    _columns = {        
        'date': fields.datetime('Sync Date', readonly=True, help="The date and time that the synchronization took place"),
        'update_file_ids': fields.one2many('lx.update.file', 'sync_id', 'Files', readonly=True, help="The updates that were created by the files"),
        'log': fields.text('Sync Log', readonly=True, help="Any error messages that occurred during the sync process"),
        'file_count': fields.function(_get_file_count, type='char', method=True, string="Files Found", help="The number of files that were imported"),
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
