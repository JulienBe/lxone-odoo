from copy import deepcopy
from openerp.osv import osv, fields

class oe_lx(object):
    """
    Define sync fields that all uploadable oe objects should have
    """
    
    def _get_files_sent(self, cr, uid, ids, field_name, arg, context=None):
        """
        Get ids for lx.file.sent records that link to ids
        """
        res = dict.fromkeys(ids, [])
        for obj_id in ids:
            cr.execute('select id from lx_file_sent where record_id = %s', ('%s,%s' % (self._name, obj_id),))
            file_ids = cr.fetchall()            
            res[obj_id] = file_ids and list(file_ids[0]);
        return res
    
    _lx_columns = {
       'lx_file_sent_id': fields.function(_get_files_sent, type="one2many", obj="lx.file.sent", method=True, string="Files Sent", 
                                          help="The files sent to LX1 for this record")
   }

    def __init__(self, pool, cr):
        """ OE will only merge _columns dicts for classes inheriting from osv.osv, so do it here manually """
        self._columns = dict(self._lx_columns.items() + self._columns.items())
        return super(oe_lx, self).__init__(pool, cr)
