from openerp.osv import osv, fields
from openerp.tools.translate import _

from picklingtools.xmldumper import *
from picklingtools import xml2dict
import json

class lx_update_file(osv.osv):
    """
    This object represents an XML file downloaded from LX1. The original XML contents is saved
    in the xml field. The xml is then parsed and the resulting data is saved in the parsed_xml field.
    
    Next step is to create lx.update.node objects from the data. The state represents this objects
    progression through the parse / node generation process. 
    """

    _name = 'lx.update.file'
    _rec_name = 'file_name'

    _columns = {
        'create_date' : fields.datetime('Create Date', readonly=True),
        'update_node_ids': fields.one2many('lx.update.node', 'update_file_id', 'Updates'),
        'sequence': fields.char('File Processing Sequence', required=True, readonly=True),
        'state': fields.selection( (
                ('to_parse', 'To Parse'), 
                ('to_generate_update_nodes', 'To Generate Updates'), 
                ('awaiting_updates', 'Waiting For Update Execution'),
                ('done', 'Fully Processed'),
            ), 'State'),
        'failed': fields.boolean('Failed'),
        'xml': fields.text('XML Data', required=True,),
        'parsed_xml': fields.text('Parsed XML Data'),
        'result': fields.text('Failure Message', readonly=True),
        'file_name': fields.char('File Name', size=64, required=True, readonly=True),
    }

    _defaults = { 
        'state': 'to_parse',
        'sequence': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'lx.update.file')
    }
    
    def write(self, cr, uid, ids, vals, context=None):
        """
        When changing state, automatically set failed to False
        """
        if 'state' in vals:
            vals['failed'] = False
        return super(lx_update_file, self).write(cr, uid, ids, vals, context=context)

    def parse(self, cr, uid, ids, context=None):
        """
        Sorts IDs by their sequence, parse them, then set state to to_generate_update_nodes
        """
        update_files = self.read(cr, uid, ids, ['sequence'], context=context)
        update_files.sort(key=lambda update_file: int(update_file['sequence']))
        parse_result = dict.fromkeys(ids)
        
        for update_file in update_files:
            update_file = self.browse(cr, uid, update_file['id'], context=context)
            
            if update_file.state != 'to_parse':
                continue
            
            # do parse
            try:
                xml = update_file.xml.decode("utf-8-sig").encode("utf-8")
                parsed_xml = xml2dict.ConvertFromXML(xml)
                parsed_xml = json.dumps(parsed_xml, indent=4)
                
                # change state
                update_file.write({'state': 'to_generate_update_nodes', 'parsed_xml': parsed_xml})
                parse_result[update_file['id']] = True
                
            except Exception, e:
                result = 'Error while parsing: %s' % str(e)
                update_file.write({'failed': True, 'result': result})
                parse_result[update_file['id']] = False
                
        return parse_result

    def parse_all(self, cr, uid, ids=[], context=None):
        """ Gets ids for all files whose state is not parsed and calls parse on them """
        all_ids = self.search(cr, uid, [('state', '!=', 'parsed')], context=context)
        return self.parse(cr, uid, all_ids)

    def generate_update_nodes(self, cr, uid, ids, context=None):
        """
        Generates an lx.update.node for each lx.update.file 
        """
        update_files = self.read(cr, uid, ids, ['sequence'], context=context)
        update_files.sort(key=lambda update_file: int(update_file['sequence']))
        generate_result = dict.fromkeys(ids)
        
        for update_file in update_files:
            update_file = self.browse(cr, uid, update_file['id'], context=context)
            
            if update_file.state != 'to_generate_update_nodes':
                continue
            
            # generate updates
            try:
                data = eval(update_file.parsed_xml)
                if not isinstance(data, list):
                    data = [data]
                
                for node_index in xrange(0, len(data)):
                    node = data[node_index]
                    
                    node_obj = self.pool.get('lx.update.node')
                    vals = {
                        'update_file_id': update_file.id,
                        'object_type': 'TEST',
                        'data': json.dumps(node, indent=4),
                        'node_number': node_index + 1,
                    }
                    node_obj.create(cr, uid, vals, context=context)
                    
                update_file.write({'state': 'awaiting_updates'})
                
            except Exception, e:
                result = 'Error while executing the update: %s' % str(e)
                update_file.write({'failed': True, 'result': result})
    
    def generate_all_update_nodes(self, cr, uid, ids, context=None):
        """ Gets ids for all files whose state is to_generate_update_nodes and calls generate_update_nodes on them """
        all_ids = self.search(cr, uid, [('state', '=', 'to_generate_update_nodes')], context=context)
        return self.generate_update_nodes(cr, uid, all_ids)
    
    def execute_update_nodes(self, cr, uid, ids, context=None):
        """ trigger execution of updates linked to this file """
        for update_file in self.browse(cr, uid, ids, context=context):
            
            if update_file.state != 'awaiting_updates':
                continue
            
            for update_node in update_file.update_node_ids:
                update_node.execute()
    
    def check_still_waiting(self, cr, uid, ids, context=None):
        """ If all update_node_ids are in state executed, mark update.file state as done """
        for update_file in self.browse(cr, uid, ids, context=context):
            
            if update_file.state != 'awaiting_updates':
                continue
                
            if all([node.state == 'executed' for node in update_file.update_node_ids]):
                update_file.write({'state': 'done'})
