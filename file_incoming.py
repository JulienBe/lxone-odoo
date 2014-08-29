# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _

from picklingtools.xmldumper import *
from picklingtools import xml2dict
import json

from auto_vivification import AutoVivification
from manager import get_lx_data_subclass

class lx_file_incoming(osv.osv):
    """
    This object represents an XML file downloaded from LX1. The original XML contents is saved
    in the xml field. The xml is then parsed and the resulting data is saved in the parsed_xml field.
    
    Next step is to create lx.update objects from the data. The state represents this objects
    progression through the parse / update generation process. 
    """

    _name = 'lx.file.incoming'
    _rec_name = 'xml_file_name'

    _columns = {
        'create_date' : fields.datetime('Create Date', readonly=True),
        'sync_id': fields.many2one('lx.sync', 'Synchronization', help="The synchronization that was responsible for creating this file"),
        'update_ids': fields.one2many('lx.update', 'file_incoming_id', 'Updates', help="Updates that this file created"),
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
        'xml_file_name': fields.char('File Name', size=64, required=True, readonly=True, help="The name of the file that contained the XML"),
    }

    _defaults = { 
        'state': 'to_parse',
        'sequence': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'lx.file.incoming')
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
        return super(lx_file_incoming, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        """ When changing state, automatically set failed to False, and sanitize values """
        if 'state' in vals:
            vals['failed'] = False
        
        vals = self._sanitize_values(vals)
        
        return super(lx_file_incoming, self).write(cr, uid, ids, vals, context=context)

    def parse(self, cr, uid, ids, context=None):
        """
        Sorts IDs by their sequence, parse them, then set state to to_generate_updates
        """
        files_incoming = self.read(cr, uid, ids, ['sequence'], context=context)
        files_incoming.sort(key=lambda file_incoming: int(file_incoming['sequence']))
        parse_result = dict.fromkeys(ids)
        
        for file_incoming in files_incoming:
            file_incoming = self.browse(cr, uid, file_incoming['id'], context=context)
            
            if file_incoming.state != 'to_parse':
                continue
            
            # do parse
            try:
                parsed_xml = xml2dict.ConvertFromXML(file_incoming.xml) # step inside to find out how to include XML_LOAD_USE_OTABS option
                
                # work out object type so it can be written to file.incoming
                object_type = self._get_object_type(cr, uid, parsed_xml)
                
                # change state
                file_incoming.write({
                                     'state': 'to_generate_updates', 
                                     'parsed_xml': parsed_xml,
                                     'object_type': object_type,
                                    })
                parse_result[file_incoming.id] = True
                
            except Exception, e:
                result = 'Error while parsing: %s' % unicode(e)
                file_incoming.write({'failed': True, 'result': result})
                parse_result[file_incoming.id] = False
                
        return parse_result

    def parse_all(self, cr, uid, ids=[], context=None):
        """ Gets ids for all files whose state is not parsed and calls parse on them """
        all_ids = self.search(cr, uid, [('state', '=', 'to_parse')], context=context)
        return self.parse(cr, uid, all_ids, context=context)
    
    def _get_object_type(self, cr, uid, parsed_xml):
        """ 
        Works out the object type from the parsed xml 
        @param dict parsed_xml: dictionary representing the xml incoming for the file
        """
        if 'ServiceRequestHeader' in parsed_xml:
            return parsed_xml['ServiceRequestHeader']['MessageIdentifier']
        elif 'out:ServiceDefinition' in parsed_xml:
            if parsed_xml['__attrs__']['xmlns:out'] == 'http://www.aqcon.com/lxone/outboundService':
                return 'OutboundService'
        else:
            raise ValueError('Could not determine an appropriate object type for this file')
    
    def get_data_for_updates(self, cr, uid, data, header, namespace, object_type, context=None):
        """ Calls get_data_for_updates on the appropriate lx_data subclass """
        cls = get_lx_data_subclass(object_type)
        return cls.get_data_for_updates(data, header, namespace)
    
    def generate_updates(self, cr, uid, ids, context=None):
        """
        Generates an lx.update for each lx.file.incoming 
        """
        files_incoming = self.read(cr, uid, ids, ['sequence'], context=context)
        files_incoming.sort(key=lambda file_incoming: int(file_incoming['sequence']))
        generate_result = dict.fromkeys(ids)
        
        for file_incoming in files_incoming:
            file_incoming = self.browse(cr, uid, file_incoming['id'], context=context)
            
            if file_incoming.state != 'to_generate_updates':
                continue
            
            # generate updates
            try:
                activity = 'evalling the data'
                data = eval(file_incoming.parsed_xml)
                prefix = ''
                
                # seperate service definition from service header
                if ':' in data.keys()[0]:
                    prefix = data.keys()[0].split(':')[0] + ':'
                    
                content_node_name = data[prefix + 'ServiceDefinition'].keys()[0]
                namespace = data['__attrs__']
                header = data[prefix + 'ServiceHeader']
                data = data[prefix + 'ServiceDefinition'][content_node_name]
                
                if not isinstance(data, list):
                    data = [data]
                
                # extract the data and data header from the data
                activity = 'reorganising the data'
                data_for_updates = self.get_data_for_updates(cr, uid, data, header, namespace, file_incoming.object_type, context)
                
                if not isinstance(data_for_updates, list):
                    data_for_updates = [data_for_updates]
                
                # create updates for each data_for_updates element in the list, 
                # and (optionally) save the header_for_updates on each update for future reference
                activity = 'creating the updates'
                for update_index in xrange(0, len(data_for_updates)):
                    update = data_for_updates[update_index]
                    
                    update_obj = self.pool.get('lx.update')
                    vals = {
                        'file_incoming_id': file_incoming.id,
                        'object_type': file_incoming.object_type,
                        'data': update,
                        'node_number': update_index + 1,
                    }
                    update_obj.create(cr, uid, vals, context=context)
                    
                file_incoming.write({'state': 'awaiting_updates'})
                
            except Exception, e:
                result = 'Error while %s: %s' % (activity, unicode(e))
                file_incoming.write({'failed': True, 'result': result})
    
    def generate_all_updates(self, cr, uid, ids=[], context=None):
        """ Gets ids for all files whose state is to_generate_updates and calls generate_updates on them """
        all_ids = self.search(cr, uid, [('state', '=', 'to_generate_updates')], context=context)
        return self.generate_updates(cr, uid, all_ids, context=context)
    
    def execute_updates(self, cr, uid, ids, context=None):
        """ trigger execution of updates """
        for file_incoming in self.browse(cr, uid, ids, context=context):
            
            if file_incoming.state != 'awaiting_updates':
                continue
            
            for update in file_incoming.update_ids:
                update.execute()
                
    def execute_all_updates(self, cr, uid, ids=[], context=None):
        """ Gets ids for all files whose state is awaiting_updates and calls execute_updates on them """
        all_ids = self.search(cr, uid, [('state', '=', 'awaiting_updates')], context=context)
        return self.execute_updates(cr, uid, all_ids, context=context)
    
    def check_still_waiting(self, cr, uid, ids, context=None):
        """ If all update_ids are in state executed, mark update.file state as done """
        for file_incoming in self.browse(cr, uid, ids, context=context):
            
            if file_incoming.state != 'awaiting_updates':
                continue
                
            if all([update.state == 'executed' for update in file_incoming.update_ids]):
                file_incoming.write({'state': 'done'})

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Cannot Delete'), _('Deletion has been disabled for file records because it is important to maintain a complete audit trail'))
