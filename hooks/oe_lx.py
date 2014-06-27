from copy import deepcopy
import HTMLParser
import base64

from openerp.osv import osv, fields
from openerp.tools.translate import _

from openerp.addons.lx_one.tools import get_config
from lx_data import lx_data

class oe_lx(object):
    """
    Define fields and methods that all uploadable oe objects should have
    """
    html_parser = HTMLParser.HTMLParser()
    
    def _get_files_outgoing(self, cr, uid, ids, field_name, arg, context=None):
        """
        Get ids for lx.file.outgoing records that link to ids
        """
        res = dict.fromkeys(ids, [])
        for obj_id in ids:
            record_reference = '%s,%s' % (self._name, obj_id)
            cr.execute("""
                SELECT id FROM lx_file_outgoing 
                WHERE record_id = %s
                OR record_names ilike %s
            """, [record_reference, '%' + record_reference + '%'])
            file_ids = cr.fetchall()            
            res[obj_id] = file_ids and list(file_ids[0]);
        return res
    
    _lx_columns = {
       'lx_file_outgoing_ids': fields.function(_get_files_outgoing, type="one2many", obj="lx.file.outgoing", method=True, string="Files Outgoing", 
                                          help="The files outgoing to LX1 for this record")
    }

    def __init__(self, pool, cr):
        """ OE will only merge _columns dicts for classes inheriting from osv.osv, so do it here manually """
        self._columns = dict(self._lx_columns.items() + self._columns.items())
        return super(oe_lx, self).__init__(pool, cr)
    
    def _get_names(self, cr, uid, records):
        """ Returns a human readable string of names for records """
        names = []
        for record in records:
            name_get = record.name_get()
            if name_get:
                name_get = name_get[0][1]
            names.append("%s,%s - %s" % (record._name, record.id, name_get))
        return '\n'.join(names)

    def upload(self, cr, uid, records, lx_data_subclass):
        """ 
        Should be called by child classes to handle data uploads correctly.
        This method instantiates lx_data_subclass with records (thereby calling extract on it)
        then calls generate_xml to convert the data to XML. It then uploads any _attachments, and
        finally creates a file_outgoing_obj and calls upload on it.
        @return: List of uploaded file name[s]
        """
        if not records:
            return
        
        assert issubclass(lx_data_subclass, lx_data), _("lx_data_subclass parameter should be a subclass of lx_data")
        file_outgoing_obj = self.pool.get('lx.file.outgoing')
        
        # instantiate lx_data_subclass with records, then call generate xml
        try:
            data = lx_data_subclass(records)
            xml_io = data.generate_xml()
            xml = xml_io.getvalue()
            xml = self.html_parser.unescape(xml)
            xml_io.close()
        except AssertionError as assertion_error:
            raise osv.except_osv(_("Error While Uploading:"), _(', '.join(assertion_error.args)))
        
        file_outgoing_ids = []
        records_multi = isinstance(records, list)
        
        # create file.outgoing for records
        vals = {
            'xml': xml, 
            'object_type': lx_data_subclass.object_type[0], 
        }
        
        if records_multi:
            vals['record_names'] = self._get_names(cr, uid, records) 
        else:
            vals['record_id'] = '%s,%s' % (records._name, records.id)
        
        parent_file_id = file_outgoing_obj.create(cr, uid, vals)
        file_outgoing_ids.append(parent_file_id)
        
        # create file.outgoing records for all attachments 
        for contents, name, extension, type in data._attachments:
            vals = {
                'upload_file_name': '%s.%s' % (name, extension),
                'xml': base64.encodestring(contents), 
                'object_type': 'Attachment', 
                'parent_file_id': parent_file_id,
                'content_type': 'pdf',
            }
            
            file_outgoing_ids.append(file_outgoing_obj.create(cr, uid, vals))
        
        # upload all created file.outgoing
        try:
            for file_id in file_outgoing_ids:
                file_name = file_outgoing_obj.upload(cr, uid, [file_id])
        except:
            file_outgoing_obj.delete_upload(cr, uid, file_outgoing_ids)
            raise
