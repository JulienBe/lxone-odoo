# -*- coding: utf-8 -*-
from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _

import oe_lx
from tools import get_config

def filter_inherit(inherit):
    """ Remove lx.oe from _inherit list """
    if isinstance(inherit, list):
        inherit = [n for n in inherit if n != 'lx.oe'][0]
    return inherit

def friendly_name(technical_name):
    """ try and get a friendly name from a technical name, i.e. stock.picking becomes Stock Picking """
    if isinstance(technical_name, list):
        technical_name = [n for n in technical_name if n != 'lx.oe'][0]
    return technical_name.replace('.', ' ').title()

class lx_file_sent(osv.osv):
    """
    A record is created each time a file is uploaded to LX1. It includes the XML of the uploaded file,
    a reference field pointing to the uploaded object and some time details 
    """

    _name = 'lx.file.sent'
    _rec_name = 'xml_file_name'
    _order = 'create_date DESC'

    _columns = {
        'create_date': fields.datetime('Create Date', readonly=True),
        'upload_date': fields.datetime('Upload Date', readonly=True),
        'state': fields.selection( (
                ('to_upload', 'To Upload'), 
                ('uploaded', 'Uploaded'), 
            ), 'State', help="The state represents this record's stage in the upload process", required=True),
        'failed': fields.boolean('Failed', help="Indicates there was a problem while uploading the file", readonly=True),
        'xml': fields.text('XML', required=True, help="The XML that should be uploaded to LX1"),
        'content_type': fields.selection((('xml', 'XML'), ('pdf', 'PDF')), 'Content Type', readonly=True),
        'result': fields.text('Failure Message', help="Any errors encountered during file upload will be listed here", readonly=True),
        'object_type': fields.char('Object Type', size=12, required=True, help="The type of data contained in this file", readonly=True),
        'xml_file_name': fields.char('File Name', size=64, required=True, help="The name of the file that contained the XML", readonly=True),
        'upload_file_name': fields.char('Uploaded File Name', size=64, help="The name of the file to be uploaded", readonly=True),
        'parent_file_id': fields.many2one('lx.file.sent', 'Parent File', help="This file is an attachment, so the parent file is the file referencing this attachment", readonly=True),
        'attachment_file_ids': fields.one2many('lx.file.sent', 'parent_file_id', 'Attachments', help="List of attachments uploaded with this file", readonly=True),
        'record_id': fields.reference('Record To Upload', list({(filter_inherit(model._inherit), friendly_name(model._inherit)) for model in oe_lx.oe_lx.__subclasses__()}), 128, readonly=True),
    }

    _defaults = {
        'content_type': 'xml',
        'state': 'to_upload',
        'upload_file_name': lambda obj, cr, uid, context: '%s_%s.xml' % (get_config(obj.pool, cr, 'lx_company_name'), obj.pool.get('ir.sequence').get(cr, uid, 'lx.file.sent')),
    } 
    
    def write(self, cr, uid, ids, vals, context=None):
        """ add update_date to vals automatically """
        if vals.get('state') == 'uploaded' and 'upload_date' not in vals:
            vals['upload_date'] = datetime.now()
        return super(lx_file_sent, self).write(cr, uid, ids, vals, context=context)
        
    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Cannot Delete'), _('Deletion has been disabled for file sent records because it is important to maintain a complete audit trail'))

    def upload(self, cr, uid, ids, context=None):
        """ Uploads file to ftp server then sets state to uploaded """
        lx_manager = self.pool.get('lx.manager')
        
        for file_sent in self.browse(cr, uid, ids):
            try:
                with lx_manager.connection(cr) as conn:
                    conn.upload_file_sent(cr, uid, file_sent)
                    file_sent.write({'state': 'uploaded'})
            except lx_manager.ftp_exceptions as e:
                raise except_osv(_("Upload Problem"), \
                        _("".join(["There was a problem uploading the data to the LX1 servers.\n\n",
                                   "Please check your connection settings in ",
                                   "Setings > Parameters > System Parameters and make sure ",
                                   "your IP is in the LX1 FTP whitelist.\n\n",
                                   "%s""" % unicode(e)])))
