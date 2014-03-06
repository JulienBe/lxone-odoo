from copy import deepcopy
from openerp.osv import osv, fields

class oe_lx(object):
    """
    Define sync fields that all uploadable oe objects should have
    """
    
    _lx_columns = {
       'lx_file_sent_id': fields.one2many('lx.file.sent', 'record_id', 'Files Sent', help="The files sent to LX1 for this record")
   }

    def __init__(self, pool, cr):
        """ OE will only merge _columns dicts for classes inheriting from osv.osv, so do it here manually """
        self._columns = dict(self._lx_columns.items() + self._columns.items())
        return super(oe_lx, self).__init__(pool, cr)
