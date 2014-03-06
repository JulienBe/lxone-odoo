from copy import deepcopy
from openerp.osv import osv, fields

class oe_lx(osv.osv):
    """
    Define sync fields that all uploadable oe objects should have
    """
    _name = 'lx.oe'
    _auto = False
    
    _columns = {
       'lx_file_sent_id': fields.one2many('lx.file.sent', 'Files Sent', help="The files sent to LX1 for this record")
   }
