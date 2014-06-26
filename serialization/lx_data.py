import StringIO
from datetime import datetime
from collections import OrderedDict

from openerp.osv.orm import browse_record
from openerp.osv.osv import except_osv
from openerp.tools.translate import _

from openerp.addons.lx_one.tools import string_to_file_name
from openerp.addons.lx_one.picklingtools.xmldumper import *
from openerp.addons.lx_one.picklingtools import xml2dict

class lx_data(object):
    """
    Serialization interface between python dicts and LX1 XML. Designed to be inherited
    so you can implement your own data input and output functions that build
    the self.data AutoVivification object (See lx_sales_order class for an example).

    Don't forget to set the object_type variable to define the xml data type. When we 
    execute an update, we choose which lx_data subclass to hand the data 
    to based on the object_type of the class and the file.

    After building the self.data dict, this object is passed to the upload_data function
    of the lx_connection object. It will call generate_xml to convert the self.data dict
    into an xml file, then upload it to the server.

    Alternatively, this class can be used to convert an LX1 xml file into an lx_data 
    dict by passing the XML into the constructor.
    """

    def __init__(self, data=None):
        """ Either parse XML from LX1, or call self.extract on a browse_record """
        super(lx_data, self).__init__()
        
        # clear instance properties
        self._attachments = []
        self.upload_file_name = ''
        self.browse_record = None

        # process the data to be uploaded
        if data and type(data) is browse_record:
            # single browse record
            self.browse_record = data
            self._validate_required_fields()
            self.extract(data)
        elif isinstance(data, list) and all([elem for elem in data if isinstance(elem, browse_record)]):
            # list of browse records
            self.browse_record = data
            assert len(set([rec._name for rec in data])) == 1, 'Cannot mix browse record object types'
            map(self._validate_required_fields, data)
            self.extract(data)
        elif data and isinstance(data, (dict, OrderedDict, list)):
            # already extracted object?
            self.data = data
        elif data:
            # invalid type
            raise TypeError('Data must be a browse record, dict, OrderedDict or list')

    # list of file name prefix's that this class should handle when receiving them from LX1
    object_type = []
    
    # List of fields that should be truthy on the browse record. See _validate_required_fields
    required_fields = []
    
    # Used in the xml template if _use_xml_template is True. Should be set in child classes that are extracted
    message_identifier = None
    
    # file name generated and set by the upload function
    upload_file_name = ''
    
    # When instantialising from a browse_record, save a reference to it  
    browse_record = None
    
    # extract function adds tuples containing attachment (contents, name, extension, type) to be uploaded along with main file 
    _attachments = None

    # Use the generic xml template defined in generate_xml
    _use_xml_template = True
    
    def _validate_required_fields(self, record=None):
        """ 
        Check that all required_fields are satisfied, otherwise
        raise an osv exception with a description of the browse record and fields affected.
        
        Works on many2one relational fields using dot notation
        And one2many relational field if the o2m field is the first field in the chain.
        o2m fields should be written like [field_name].
        
        Examples:
        
        date
        product_id.name
        [move_lines].name  
        """
        if not record:
            record = self.browse_record
        
        if not record:
            raise ValueError('Missing record or self.browse_record')
        
        invalid_fields = []
        
        # Iterate over required_fields checking if they have been satisfied
        for required_field in self.required_fields:
            if '.' not in required_field:
                # simple field check
                if not record[required_field]:
                    invalid_fields.append(required_field)
            else:
                # relational field check
                def check(self, target, record, fields):
                    """ Convert fields into a dot notation query and execute it on target """
                    query = '%s.%s' % (target, '.'.join(fields))
                    try:
                        res = eval(query)
                        if isinstance(res, (unicode, str)):
                            res = res.strip()
                        if not res:
                            invalid_fields.append(required_field)
                    except Exception as e:
                        invalid_fields.append(required_field)
                
                fields = required_field.split('.')
                
                # check for one2many type field
                if fields[0][0:1] == '[' and fields[0][-1:] == ']':
                    one2many_field = fields[0][1:-1]
                    if not record[one2many_field]:
                        invalid_fields.append(one2many_field)
                    else:
                        for record_index in xrange(0, len(record[one2many_field])):
                            target = 'record.%s[%d]' % (one2many_field, record_index)
                            check(self, target, record, fields[1:])
                else:
                    check(self, 'record', record, fields)
        
        # raise exception if necessary
        if invalid_fields:
            invalid_fields_str = ''
            for field in invalid_fields:
                if '.' in field:
                    field_parts = map(lambda p: '_' in p and p.split('_')[0] or p, field.split('.'))
                    invalid_fields_str += '\n%s' % ' -> '.join(map(lambda p: p.title().replace('[',''), field_parts))
                else:
                    invalid_fields_str += '\n%s' % field
            
            except_args = (
                               record._description,
                               record[record._rec_name],
                               invalid_fields_str
                           )
            raise except_osv(_("Required Fields Invalid"), _('The following required fields were invalid for %s "%s": \n\n %s') % except_args)
        else:
            return None

    def safe_get(self, dictionary, key):
        """ Returns self.data[key] or None if it does not exist """
        if key in dictionary:
            return dictionary[key]
        else:
            return None

    def insert_data(self, insert_target, params):
        """
        Insert keys and values from params into self.data at insert_target.
        Calling this method twice on the same key will convert the key from a dict
        to a list of dicts. In this way it can handle multiple xml nodes with
        the same name.

        @param dict params: keys and values to insert into self.data
        @param str insert_target: dot separated values for insert target. For example
                                  'order.customer' inserts to self.data['order']['customer']
        """
        # save reference to the target key inside the nested dictionary self.data
        target = self.data
        for target_key in insert_target.split('.'):
            parent = target
            target = target[target_key]

        # have we already saved data to this key? If yes, convert it to a list of dicts
        if isinstance(target, (AutoVivification, OrderedDict)) and len(target) != 0:
            autoviv = False
            parent[target_key] = [target]
            target = parent[target_key]
        elif isinstance(target, list):
            autoviv = False
        else:
            autoviv = True

        if autoviv:
            # add data to the empty dict like normal
            for param_name in params:
                param_value = params[param_name]

                if not param_name == 'self':
                    target[param_name] = param_value
        else:
            # create new dict to be added to the list of dicts
            val = AutoVivification()
            for param_name in params:
                param_value = params[param_name]

                if not param_name == 'self':
                    val[param_name] = param_value

            target.append(val)
            
    def add_attachments(self, pool, cr, uid, model, ids, report_name, file_name_prefix, report_type, data_type='pdf'):
        """ 
        Generate attachments for ids and insert the data into self._attachments
        @param dict pool: openerp object pool
        @param string model: The model for which to create the report
        @param list ids: The ids of the records for which to create the report
        @param string report_name: The internal technical name of the report to be used
        @param string file_name_prefix: The prefix for the file name to be added to _ObjectId
        @param string report_type: the type string to be entered into the tuple. This will be used when uploading data to LX1
        @param string data_type: the type of data returned by this call. Used internally by the report mechanism
        """
        report_obj = pool.get('ir.actions.report.xml')
        if not hasattr(ids, '__iter__'):
            ids = [ids]
            
        report_data = {'report_type': data_type, 'model': model}
        
        for obj_id in ids:
            file_name = string_to_file_name('%s_%d' % (file_name_prefix, obj_id))
            report_contents, report_extension = report_obj.render_report(cr, uid, [obj_id], report_name, report_data)
            self._attachments.append((report_contents, file_name, report_extension, report_type))

    def generate_xml(self):
        """ 
        If _use_xml_template is true, puts self.data inside the appropriate node in the XML header and then 
        Returns a StringIO containing an XML representation of self.data nested dict 
        """
        # add xml template if self._use_xml_template is truthy 
        if self._use_xml_template:
            assert self.message_identifier, "message_identifier variable not set!"
            
            content = self.data
            self.data = OrderedDict([
                ('__attrs__', OrderedDict([ # add xmlns etc to root element (ServiceRequest)
                    ('xmlns', 'http://www.aqcon.com/lxone/inboundService'),
                    ('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance'),
                    ('xsi:schemaLocation', 'http://www.aqcon.com/lxone/inboundService /home/openerp/openerp/lx-one/schemas/InboundService.xsd'),
                ])),
                ('ServiceRequestHeader', OrderedDict([
                    ('ServiceRequestor', 'LX One'),
                    ('ServiceProvider', 'LX One'),
                    ('ServiceIdentifier', 'OpenERP'),
                    ('MessageIdentifier', self.message_identifier),
                    ('RequestDateTime', datetime.now().isoformat()),
                    ('ResponseRequest', 'Never'),
                ])),
                ('ServiceDefinition', content),
            ])
        
        # validate self.data and convert autoviv to ordered dict if needed
        self._check_ordered_dicts_only(self.data)
        
        # convert to pretty XML 
        output = StringIO.StringIO()
        xd = XMLDumper(output, XML_DUMP_PRETTY | XML_STRICT_HDR)
        xd.XMLDumpKeyValue('ServiceRequest', self.data)
        output.seek(0)
        return output
    
    def _check_ordered_dicts_only(self, struct):
        """ 
        Looks at every element recursively in struct and raises a TypeError
        if it finds a regular dict 
        """
        for key in struct:
            val = struct[key]
            if type(val) == dict:
                raise TypeError('Regular dict found! Should only use ordered dicts')
            elif type(val) == OrderedDict:
                self._check_ordered_dicts_only(val)

    @staticmethod
    def reorganise_data(data, header, namespace):
        """
        This method is called by the poll function to give each object type the opportunity
        to reorganise the data received from LX1, after it is parsed from the XML file and
        before it is used to generate updates.
        
        @param AutoVivification data: The parsed XML from LX1
        @return data 
        """
        return data, header, namespace

    def extract(self, record):
        """
        Called by the constructor when given a browse_record. This method should
        extract the browse_record's data into the self.data object.

        This method is a stub that you have to implement in an inheriting model.
        @param browse_record record: browse_record from which to extract data
        @return self: allow for chaining
        """
        raise NotImplemented('Please implement this method in your inherited model')

    def process(self, pool, cr):
        """
        Called by process_all which is triggered by the OpenERP poll function.
        Override this method to do something with self.data in OpenERP. Any exceptions
        should be raised.

        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        """
        raise NotImplemented('Please implement this method in your inherited model')
