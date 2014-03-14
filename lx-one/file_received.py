# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _

from picklingtools.xmldumper import *
from picklingtools import xml2dict
import json

from auto_vivification import AutoVivification
from manager import get_lx_data_subclass

class lx_file_received(osv.osv):
    """
    This object represents an XML file downloaded from LX1. The original XML contents is saved
    in the xml field. The xml is then parsed and the resulting data is saved in the parsed_xml field.
    
    Next step is to create lx.update objects from the data. The state represents this objects
    progression through the parse / update generation process. 
    """

    _name = 'lx.file.received'
    _rec_name = 'file_name'

    _columns = {
        'create_date' : fields.datetime('Create Date', readonly=True),
        'sync_id': fields.many2one('lx.sync', 'Synchronization', help="The synchronization that was responsible for creating this file"),
        'update_ids': fields.one2many('lx.update', 'file_received_id', 'Updates', help="Updates that this file created"),
        'sequence': fields.char('File Processing Sequence', required=True, readonly=True, help="This field determines the order that files will be processed"),
        'state': fields.selection( (
                ('to_parse', 'To Parse'), 
                ('to_generate_updates', 'To Generate Updates'), 
                ('awaiting_updates', 'Waiting For Update Execution'),
                ('done', 'Fully Processed'),
            ), 'State', help="The state represents this record's stage in the workflow process"),
        'failed': fields.boolean('Failed', help="Indicates there was a problem while processing the file"),
        'xml': fields.text('XML Data', required=True, help="The XML that was inside the file from LX1"),
        'parsed_xml': fields.text('Parsed XML Data', help="The result of parsing the XML data from the file"),
        'result': fields.text('Failure Message', readonly=True, help="Any errors encountered during processing the file will be listed here"),
        'object_type': fields.char('Object Type', size=128, readonly=True, help="The type of data contained in this file"),
        'file_name': fields.char('File Name', size=64, required=True, readonly=True, help="The name of the file that contained the XML"),
    }

    _defaults = { 
        'state': 'to_parse',
        'sequence': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'lx.file.received')
    }
    
    def _sanitize_values(self, vals):
        """ Convert XML to use XML entities and pretty print parsed_xml """
        if vals.get('parsed_xml'):
            if isinstance(vals['parsed_xml'], (dict, list, tuple, AutoVivification)):
                vals['parsed_xml'] = json.dumps(vals['parsed_xml'], indent=4, ensure_ascii=False)
            
        if 'state' in vals and 'result' not in vals:
            vals['result'] = ''
            
        return vals
    
    def create(self, cr, uid, vals, context=None):
        """ Sanitize values """
        vals = self._sanitize_values(vals)
        return super(lx_file_received, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        """ When changing state, automatically set failed to False, and sanitize values """
        if 'state' in vals:
            vals['failed'] = False
        
        vals = self._sanitize_values(vals)
        
        return super(lx_file_received, self).write(cr, uid, ids, vals, context=context)

    def parse(self, cr, uid, ids, context=None):
        """
        Sorts IDs by their sequence, parse them, then set state to to_generate_updates
        """
        files_received = self.read(cr, uid, ids, ['sequence'], context=context)
        files_received.sort(key=lambda file_received: int(file_received['sequence']))
        parse_result = dict.fromkeys(ids)
        
        for file_received in files_received:
            file_received = self.browse(cr, uid, file_received['id'], context=context)
            
            if file_received.state != 'to_parse':
                continue
            
            # do parse
            try:
                parsed_xml = xml2dict.ConvertFromXML(file_received.xml) # step inside to find out how to include XML_LOAD_USE_OTABS option
                
                # work out object type so it can be written to file.received
                object_type = self._get_object_type(cr, uid, parsed_xml)
                
                # change state
                file_received.write({
                                     'state': 'to_generate_updates', 
                                     'parsed_xml': parsed_xml,
                                     'object_type': object_type,
                                    })
                parse_result[file_received.id] = True
                
            except Exception, e:
                result = 'Error while parsing: %s' % unicode(e)
                file_received.write({'failed': True, 'result': result})
                parse_result[file_received.id] = False
                
        return parse_result

    def parse_all(self, cr, uid, ids=[], context=None):
        """ Gets ids for all files whose state is not parsed and calls parse on them """
        all_ids = self.search(cr, uid, [('state', '=', 'to_parse')], context=context)
        return self.parse(cr, uid, all_ids, context=context)
    
    def _get_object_type(self, cr, uid, parsed_xml):
        """ 
        Works out the object type from the parsed xml 
        @param dict parsed_xml: dictionary representing the xml received for the file
        """
        return parsed_xml['ServiceRequestHeader']['MessageIdentifier']
    
    def reorganise_data(self, cr, uid, data, header, namespace, object_type, context=None):
        """ Calls reorganise_data on the appropriate lx_data subclass """
        cls = get_lx_data_subclass(object_type)
        return cls.reorganise_data(data, header, namespace)
    
    def generate_updates(self, cr, uid, ids, context=None):
        """
        Generates an lx.update for each lx.file.received 
        """
        files_received = self.read(cr, uid, ids, ['sequence'], context=context)
        files_received.sort(key=lambda file_received: int(file_received['sequence']))
        generate_result = dict.fromkeys(ids)
        
        for file_received in files_received:
            file_received = self.browse(cr, uid, file_received['id'], context=context)
            
            if file_received.state != 'to_generate_updates':
                continue
            
            # generate updates
            try:
                activity = 'evalling the data'
                data = eval(file_received.parsed_xml)
                
                # seperate service definition from service header
                content_node_name = data['ServiceDefinition'].keys()[0]
                namespace = data['__attrs__']
                header = data['ServiceRequestHeader']
                data = data['ServiceDefinition'][content_node_name]
                
                if not isinstance(data, list):
                    data = [data]
                
                # reorganise the data for processing
                activity = 'reorganising the data'
                data, header, namespace = self.reorganise_data(cr, uid, data, header, namespace, file_received.object_type, context)
                
                activity = 'creating the updates'
                for update_index in xrange(0, len(data)):
                    update = data[update_index]
                    
                    update_obj = self.pool.get('lx.update')
                    vals = {
                        'file_received_id': file_received.id,
                        'object_type': file_received.object_type,
                        'data': update,
                        'node_number': update_index + 1,
                    }
                    update_obj.create(cr, uid, vals, context=context)
                    
                file_received.write({'state': 'awaiting_updates'})
                
            except Exception, e:
                result = 'Error while %s: %s' % (activity, unicode(e))
                file_received.write({'failed': True, 'result': result})
    
    def generate_all_updates(self, cr, uid, ids=[], context=None):
        """ Gets ids for all files whose state is to_generate_updates and calls generate_updates on them """
        all_ids = self.search(cr, uid, [('state', '=', 'to_generate_updates')], context=context)
        return self.generate_updates(cr, uid, all_ids, context=context)
    
    def execute_updates(self, cr, uid, ids, context=None):
        """ trigger execution of updates """
        for file_received in self.browse(cr, uid, ids, context=context):
            
            if file_received.state != 'awaiting_updates':
                continue
            
            for update in file_received.update_ids:
                update.execute()
    
    def execute_all_updates(self, cr, uid, ids=[], context=None):
        """ Gets ids for all files whose state is awaiting_updates and calls execute_updates on them """
        all_ids = self.search(cr, uid, [('state', '=', 'awaiting_updates')], context=context)
        return self.execute_updates(cr, uid, all_ids, context=context)
    
    def check_still_waiting(self, cr, uid, ids, context=None):
        """ If all update_ids are in state executed, mark update.file state as done """
        for file_received in self.browse(cr, uid, ids, context=context):
            
            if file_received.state != 'awaiting_updates':
                continue
                
            if all([update.state == 'executed' for update in file_received.update_ids]):
                file_received.write({'state': 'done'})

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Cannot Delete'), _('Deletion has been disabled for file records because it is important to maintain a complete audit trail'))
