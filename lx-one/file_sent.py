# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _

import oe_lx

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
    _rec_name = 'file_name'

    _columns = {
        'create_date': fields.datetime('Create Date', readonly=True),
        'upload_date': fields.datetime('Upload Date', readonly=True),
        'state': fields.selection( (
                ('to_upload', 'To Upload'), 
                ('uploaded', 'Uploaded'), 
            ), 'State', help="The state represents this record's stage in the upload process", required=True),
        'failed': fields.boolean('Failed', help="Indicates there was a problem while uploading the file", readonly=True),
        'xml': fields.text('XML Data', required=True, help="The XML that should be uploaded to LX1"),
        'result': fields.text('Failure Message', help="Any errors encountered during file upload will be listed here", readonly=True),
        'object_type': fields.char('Object Type', size=12, required=True, help="The type of data contained in this file", readonly=True),
        'file_name': fields.char('File Name', size=64, required=True, help="The name of the file that contained the XML", readonly=True),
        'record_id': fields.reference('Record To Upload', list({(filter_inherit(model._inherit), friendly_name(model._inherit)) for model in oe_lx.oe_lx.__subclasses__()}), 128, required=True),
    }

    _defaults = { 
        'state': 'to_upload',
    }

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Cannot Delete'), _('Deletion has been disabled for file sent records because it is important to maintain a complete audit trail'))
