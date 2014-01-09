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

class ads_data(object):
    """
    Serialization interface between python dicts and ADS XML. Designed to be inherited
    so you can implement your own data input and output functions that build
    the self.data AutoVivification object (See ads_sales_order class for an example).

    Don't forget to set the file_name_prefix and xml_root variables to define the xml
    file name prefix (XXXX-YYYMMDD.xml) and xml file root element name. When the poll
    function processes a file, it chooses which ads_data subclass to hand the data to
    based on the file_name_prefix of the class and the file.

    After building the self.data dict, this object is passed to the upload_data function
    of the ads_connection object. It will call generate_xml to convert the self.data dict
    into an xml file, then upload it to the server.

    Alternatively, this class can be used to convert an ADS xml file into an ads_data 
    dict by passing the XML into the constructor.
    """

    def __init__(self, data=None):
        """ Either parse XML from ADS, or call self.extract on a browse_record """
        super(ads_data, self).__init__()
        self.data = AutoVivification()

        if data and isinstance(data, (str, unicode)):
            self.data = xml2dict.ConvertFromXML(data)
            self.data = AutoVivification.dict_to_auto_vivification(self.data)
        elif data and isinstance(data, browse_record):
            self.extract(data)
            self.browse_record = data
        elif data:
            raise TypeError('XML must be a string, unicode or AutoVivification object')

    # list of file name prefix's that this class should handle when receiving them from ADS
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

    def upload(self, cr, ads_manager):
        """
        Upload this object to ADS
        @param ads_manager ads_manager: the ads.manager object from the OpenERP pool
        """
        try:
            with ads_manager.connection(cr) as conn:
                self.file_name = conn.upload_data(self)
        except ads_manager.ftp_exceptions as e:
            raise except_osv(_("Upload Problem"), \
                    _("".join(["There was a problem uploading the data to the ADS servers.\n\n",
                               "Please check your connection settings in ",
                               "Setings > Parameters > System Parameters and make sure ",
                               "your IP is in the ADS FTP whitelist.\n\n",
                               "%s""" % unicode(e)])))
        return True

    def extract(self, record):
        """
        Called by the constructor when given a browse_record. This method should
        extract the browse_record's data into the self.data object.

        This method is a stub that you have to implement in an inheriting model.
        @param browse_record record: browse_record from which to extract data
        @return self: allow for chaining
        """
        raise NotImplemented('Please implement this method in your inherited model')

    def process_all(self, pool, cr, ads_conn):
        """
        Iterates over data nodes in self.data and securely calls self.process on them, while
        catching and storing any exceptions.
        
        If self._auto_remove is true, successfully processed nodes (without exceptions) will be 
        removed from self.data.  
        
        The pre_process_hook and post_process_hook are called before and after data iteration.
        
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @param ads_connection ads_conn: Connection to the FTP server
        @returns A list of strings describing errors faced while processing the file or []
        """
        if not self.data:
            return []
        
        # get root element name
        root_key = self.data.keys()[0]

        # if only have one root element, convert it to a list for iteration
        if isinstance(self.data[root_key], AutoVivification):
            self.data[root_key] = [self.data[root_key]]

        # iterate through elements while processing them. Save errors for later
        self.errors = []
        successes = []

        # call hook
        pre_process_errors = self.pre_process_hook(pool, cr)
        assert isinstance(pre_process_errors, list), 'Pre process hook should return a list!'
        self.errors =  self.errors + pre_process_errors
        
        # iterate over data nodes and call process
        root_key = self.data.keys()[0]
        for i in range(0, len(self.data[root_key])):
            data_leaf = self.data[root_key][i]

            try:
                self.process(pool, cr, data_leaf)
                successes.append(i)
            except self.process_exceptions as e:
                self.errors.append('%s: %s' % (type(e), unicode(e)))
            
            # ping the FTP server to maintain an open connection
            ads_conn._ping()

        # call hook
        post_process_errors = self.post_process_hook(pool, cr)
        assert isinstance(post_process_errors, list), 'Post process hook should return a list!'
        self.errors =  self.errors + post_process_errors

        # Remove successfully processed nodes from self.data
        if self.data and self._auto_remove:
            root_key = self.data.keys()[0]
            for i in sorted(successes, reverse=True):
                del self.data[root_key][i]

        # Return self.errors to be handled one level up
        return self.errors

    def pre_process_hook(self, pool, cr):
        """ Called by process_all before it calls process on data nodes. Return list of errors """
        return []

    def post_process_hook(self, pool, cr):
        """ Called by process_all after it calls process on all data nodes. Return list of errors """
        return []

    def process(self, pool, cr, data_leaf):
        """
        Called by process_all which is triggered by the OpenERP poll function.
        Override this method to do something with data_leaf in OpenERP. Any exceptions
        should be raised.

        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        """
        raise NotImplemented('Please implement this method in your inherited model')
