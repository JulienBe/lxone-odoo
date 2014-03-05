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
            self.extract(data)
            self.browse_record = data
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
    
    # file name generated and set by the upload function
    file_name = ''
    
    # When instantialising from a browse_record, save a reference to it  
    browse_record = None

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
        """ Returns a StringIO containing an XML representation of self.data nested dict """
        assert self.xml_root != None, 'The self.xml_root variable must be set in your inheriting class'
        output = StringIO.StringIO()
        xd = XMLDumper(output, XML_DUMP_PRETTY | XML_STRICT_HDR)
        xd.XMLDumpKeyValue(self.xml_root, self.data.to_dict())
        output.seek(0)
        return output

    def upload(self, cr, lx_manager):
        """
        Upload this object to LX1
        @param lx_manager lx_manager: the lx.manager object from the OpenERP pool
        """
        try:
            with lx_manager.connection(cr) as conn:
                self.file_name = conn.upload_data(self)
        except lx_manager.ftp_exceptions as e:
            raise except_osv(_("Upload Problem"), \
                    _("".join(["There was a problem uploading the data to the LX1 servers.\n\n",
                               "Please check your connection settings in ",
                               "Setings > Parameters > System Parameters and make sure ",
                               "your IP is in the LX1 FTP whitelist.\n\n",
                               "%s""" % unicode(e)])))
        return True
    
    @staticmethod
    def reorganise_data(data):
        """
        This method is called by the poll function to give each object type the opportunity
        to reorganise the data received from LX1, after it is parsed from the XML file and
        before it is used to generate update nodes.
        
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
