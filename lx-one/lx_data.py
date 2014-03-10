import sys
import StringIO
from lxml import etree
import re
from datetime import datetime

from openerp.osv.orm import browse_record
from openerp.osv.osv import except_osv
from openerp.tools.translate import _

from picklingtools.xmldumper import *
from picklingtools import xml2dict
from auto_vivification import AutoVivification

class lx_data(object):
    """
    Serialization interface between python dicts and LX1 XML. Designed to be inherited
    so you can implement your own data input and output functions that build
    the self.data AutoVivification object (See lx_sales_order class for an example).

    Don't forget to set the file_name_prefix and xml_root variables to define the xml
    file name prefix (XXXX-YYYMMDD.xml) and xml file root element name. When the poll
    function processes a file, it chooses which lx_data subclass to hand the data to
    based on the file_name_prefix of the class and the file.

    After building the self.data dict, this object is passed to the upload_data function
    of the lx_connection object. It will call generate_xml to convert the self.data dict
    into an xml file, then upload it to the server.

    Alternatively, this class can be used to convert an LX1 xml file into an lx_data 
    dict by passing the XML into the constructor.
    """

    def __init__(self, data=None):
        """ Either parse XML from LX1, or call self.extract on a browse_record """
        super(lx_data, self).__init__()
        self.data = AutoVivification()

        if data and isinstance(data, browse_record):
            self.browse_record = data
            self._missing_fields()
            self.extract(data)
        elif data and isinstance(data, (dict, list, tuple)):
            self.data = AutoVivification.dict_to_auto_vivification(data)
        elif data:
            raise TypeError('XML must be a string, unicode or AutoVivification object')

    # list of file name prefix's that this class should handle when receiving them from LX1
    file_name_prefix = []

    # name of the root xml element when generating data to upload
    xml_root = None

    # list of exceptions that this class generates during the "process" method
    process_exceptions = (Exception)

    # when processing the data, if true, auto remove nodes that are successful. Nodes left
    # over will be uploaded to the errors/ directory of the server
    _auto_remove = True
    
    # Use the generic xml template defined in generate_xml. Self.data will be nested inside the ServiceDefinition node
    _use_xml_template = True
    
    # file name generated and set by the upload function
    file_name = ''
    
    # When instantialising from a browse_record, save a reference to it  
    browse_record = None
    
    # used by the missing_fields function
    required_fields = []
    
    def _missing_fields(self):
        """ 
        Check that all required_fields are truthy in the browse_record, otherwise
        raise an osv exception with a description of the browse record and fields affected
        """
        if not self.browse_record:
            raise ValueError('Missing self.browse_record')
        
        fields_missing = [field for field in self.required_fields if not self.browse_record[field]]
        
        if fields_missing:
            except_args = (
                           self.browse_record._description,
                           self.browse_record[self.browse_record._rec_name],
                           '\n'.join(fields_missing)
                           )
            raise except_osv(_("Required Fields Missing"), _('The following required fields were missing for %s "%s": \n\n %s') % except_args)
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
        if isinstance(target, AutoVivification) and len(target) != 0:
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

    def name(self):
        """ Generate a name for the uploaded xml file """
        assert self.file_name_prefix, 'The self.file_name_prefix variable must be set in your inheriting class'
        return '%s-%s.xml' % (self.file_name_prefix[0], datetime.today().strftime('%Y%m%d-%H%M%S-%f'))

    def generate_xml(self):
        """ 
        If _use_xml_template is true, puts self.data inside the appropriate node in the XML header and then 
        Returns a StringIO containing an XML representation of self.data nested dict 
        """
        assert self.xml_root != None, 'The self.xml_root variable must be set in your inheriting class'
        
        # add xml template if self._use_xml_template is truthy 
        if self._use_xml_template:
            content = self.data
            self.data = AutoVivification({
                '__attrs__': { # add xmlns etc to root element (ServiceRequest)
                    'xmlns': 'http://www.aqcon.com/lxone/inboundService',
                    'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                    'xsi:schemaLocation': 'http://www.aqcon.com/lxone/inboundService C:/projects/pvszmd/server/java/edi/xml/v1/schemas/src/main/xsd/InboundService.xsd',
                },
                'ServiceRequestHeader': {
                    'ServiceRequestor': 'LX One',
                    'ServiceProvider': 'LX One',
                    'ServiceIdentifier': 'OpenERP',
                    'MessageIdentifier': 'OpenErpItemCreate',
                    'RequestDateTime': datetime.now().isoformat(),
                    'ResponseRequest': 'Never',
                },
                'ServiceDefinition': content,            
            })
        
        output = StringIO.StringIO()
        xd = XMLDumper(output, XML_DUMP_PRETTY | XML_STRICT_HDR)
        xd.XMLDumpKeyValue('ServiceRequest', self.data.to_dict())
        output.seek(0)
        return output

    @staticmethod
    def reorganise_data(data):
        """
        This method is called by the poll function to give each object type the opportunity
        to reorganise the data received from LX1, after it is parsed from the XML file and
        before it is used to generate updates.
        
        @param AutoVivification data: The parsed XML from LX1
        @return data 
        """
        return data

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
