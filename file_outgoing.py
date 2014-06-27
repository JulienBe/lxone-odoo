# -*- coding: utf-8 -*-
from datetime import datetime

from openerp.osv import osv, fields
from openerp.osv.osv import except_osv
from openerp.tools.translate import _

import oe_lx
from tools import get_config

class lx_file_outgoing(osv.osv):
    """
    A record is created each time a file is to be uploaded to LX1. It includes the XML of the uploaded file,
    a reference field pointing to the uploaded object and some time details 
    """

    _name = 'lx.file.outgoing'
    _rec_name = 'upload_file_name'
    _order = 'create_date DESC'
    
    _uploadable_models = [
        ('product.product', 'Product'),
        ('res.partner', 'Partner'),
        ('purchase.order', 'Purchase Order'),
        ('sale.order', 'sale Order'),
        ('stock.picking', 'Stock Picking'),
    ]

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
        'object_type': fields.char('Object Type', size=64, required=True, help="The type of data contained in this file", readonly=True),
        'upload_file_name': fields.char('Uploaded File Name', size=64, help="The name of the file to be uploaded", readonly=True),
        'parent_file_id': fields.many2one('lx.file.outgoing', 'Parent File', help="This file is an attachment, so the parent file is the file referencing this attachment", readonly=True),
        'attachment_file_ids': fields.one2many('lx.file.outgoing', 'parent_file_id', 'Attachments', help="List of attachments uploaded with this file", readonly=True),
        'record_id': fields.reference('Record To Upload', _uploadable_models, 128, readonly=True),
        'record_names': fields.text('Records To Upload', help="A list of all records that are contained in this file if more than one", readonly=True),
    }

    _defaults = {
        'content_type': 'xml',
        'state': 'to_upload',
        'upload_file_name': lambda obj, cr, uid, context: '%s_%s.xml' % (get_config(obj.pool, cr, 'lx_company_name'), obj.pool.get('ir.sequence').get(cr, uid, 'lx.file.outgoing')),
    } 
    
    def write(self, cr, uid, ids, vals, context=None):
        """ add update_date to vals automatically """
        if vals.get('state') == 'uploaded' and 'upload_date' not in vals:
            vals['upload_date'] = datetime.now()
        return super(lx_file_outgoing, self).write(cr, uid, ids, vals, context=context)
        
    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Cannot Delete'), _('Deletion has been disabled for file outgoing records because it is important to maintain a complete audit trail'))

    def upload(self, cr, uid, ids, context=None):
        """ Uploads file to ftp server then sets state to uploaded """
        lx_manager = self.pool.get('lx.manager')
        
        for file_outgoing in self.browse(cr, uid, ids):
            try:
                with lx_manager.connection(cr) as conn:
                    file_name = conn.upload_file_outgoing(cr, uid, file_outgoing)
                    file_outgoing.write({'state': 'uploaded'})
                    return file_name
            except lx_manager.ftp_exceptions as e:
                raise except_osv(_("Upload Problem"), \
                        _("".join(["There was a problem uploading the data to the LX1 servers.\n\n",
                                   "Please check your connection settings in ",
                                   "Setings > Parameters > System Parameters and make sure ",
                                   "your IP is in the LX1 FTP whitelist.\n\n",
                                   "%s""" % unicode(e)])))
                                   
    def delete_upload(self, cr, uid, ids, context=None):
        """ Deletes a file that has been uploaded """
        lx_manager = self.pool.get('lx.manager')
        
        for file_outgoing in self.browse(cr, uid, ids):
            if not file_outgoing.upload_file_name:
                continue
            
            with lx_manager.connection(cr) as conn:
                conn.delete_file_outgoing(cr, uid, file_outgoing)
                file_outgoing.write({'state': 'to_upload'})
