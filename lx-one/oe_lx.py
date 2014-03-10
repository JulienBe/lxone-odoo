from copy import deepcopy
from openerp.osv import osv, fields
from openerp.tools.translate import _

from tools import get_config
from lx_data import lx_data

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
       'lx_file_sent_ids': fields.function(_get_files_sent, type="one2many", obj="lx.file.sent", method=True, string="Files Sent", 
                                          help="The files sent to LX1 for this record")
    }

    def __init__(self, pool, cr):
        """ OE will only merge _columns dicts for classes inheriting from osv.osv, so do it here manually """
        self._columns = dict(self._lx_columns.items() + self._columns.items())
        return super(oe_lx, self).__init__(pool, cr)

    def upload(self, cr, uid, browse_record, lx_data_subclass):
        """ A convenience method for child classes to create a file.sent object and trigger upload on it """
        assert issubclass(lx_data_subclass, lx_data), _("lx_data_subclass parameter should be a subclass of lx_data")
        file_sent_obj = self.pool.get('lx.file.sent')
        
        try:
            data = lx_data_subclass(browse_record)
            xml_io = data.generate_xml()
            xml = xml_io.getvalue()
            xml_io.close()
        except AssertionError as assertion_error:
            raise osv.except_osv(_("Error While Uploading:"), _(', '.join(assertion_error.args)))
        
        vals = {
           'xml': xml, 
           'object_type': lx_data_subclass.file_name_prefix[0], 
           'record_id': '%s,%s' % (browse_record._name, browse_record.id),
        }
        
        file_id = file_sent_obj.create(cr, uid, vals)
        file_name = file_sent_obj.upload(cr, uid, [file_id])
        return file_name
