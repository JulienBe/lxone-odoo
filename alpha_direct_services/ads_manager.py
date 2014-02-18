import logging
_logger = logging.getLogger(__name__)
from openerp.osv import osv
from openerp.tools.translate import _

from ftplib import all_errors
from StringIO import StringIO

from ads_connection import ads_connection
from ads_data import ads_data
from auto_vivification import AutoVivification
from ads_purchase_order import ads_purchase_order
from ads_sales_order import ads_sales_order
from ads_product import ads_product
from ads_return import ads_return
from ads_stock import ads_stock
from ads_picking import ads_picking
from ads_file import ads_file

class ads_manager(osv.osv):
    """
    Instantiates an FTP connection wrapper object and allows polling the ADS FTP Server
    """

    _columns = {}
    _name = 'ads.manager'
    _auto = False

    _file_process_order = [
        'MVTS',# PO received
        'CREX',# SO sent
        'CRET',# return
        'STOC',# physical inventory
    ]

    ftp_exceptions = all_errors

    def connection(self, cr):
        """ Gets an instance of ads_connection class that wraps the FTP server """
        return ads_connection(self.pool, cr)

    def poll(self, cr, uid=1):
        """
        Poll the ADS FTP server, download a file list and iterate over them by oldest first,
        then by _file_process_order. 
        
        For each file, look for a child class of ads_data whose file_name_prefix field includes 
        the part before the first '-' of the file name. Download the file contents and use it
        to instantiate the found class, then call process_all on it.
        
        Any errors caught in the process are added to errors returned by the process_all
        function, and then written to the /errors/ directory as a .txt file, along with any
        data nodes left in self.data after processing. 
        """

        _logger.info(_("Polling ADS Server..."))
        files_processed = 0
        
        # get connection FTP server
        with self.connection(cr) as conn:

            conn.cd(conn._vers_client)

            # get list of files and directories and remove any files that cannot be processed
            files_and_directories = conn.ls()
            files_to_process = map(lambda f: ads_file(f), files_and_directories)
            files_to_process = filter(lambda f: f.valid, files_to_process)
            files_to_process = filter(lambda f: f.to_process(), files_to_process)
            
            # then sort by date and add to dictionary where the key is the date so we can process
            # chronologically and with file prefix order 
            files_to_process.sort(key=lambda f: f.date)
            files_by_date = AutoVivification()
            for f in files_to_process:
                if not isinstance(files_by_date[f.date], list):
                    files_by_date[f.date] = []
                files_by_date[f.date].append(f)

            try:
                # create archive and errors directory if doesn't already exist
                if 'archives' not in files_and_directories:
                    conn.mkd('archives')

                if 'errors' not in files_and_directories:
                    conn.mkd('errors')
                
                # process by earliest date first
                for date in sorted(files_by_date.keys()):
                    # then according to file_process_order
                    for prefix in self._file_process_order:
                        for file_to_process in [f for f in files_by_date[date] if f.prefix == prefix]:

                            files_processed += 1
                            file_prefix = file_to_process.prefix
                            file_name = file_to_process.file_name
                            
                            # find ads_data subclass with matching 'type' property
                            class_for_data_type = [cls for cls in ads_data.__subclasses__() if file_prefix in cls.file_name_prefix]
    
                            if class_for_data_type:
    
                                # log warning if found more than one matching class
                                if len(class_for_data_type) != 1:
                                    _logger.warn(_('The following subclasses of ads_data share the file_name_prefix: %s' % class_for_data_type))
    
                                errors = StringIO()
    
                                # catch any errors not caught by data.process etc
                                try:
                                    # Download and decode the file contents
                                    file_contents = conn.download_data(file_name).decode("utf-8-sig").encode("utf-8")
                                    
                                    # instantiate found subclass with correctly encoded file_data
                                    data = class_for_data_type[0](file_contents)
    
                                    # trigger process to import into OpenERP
                                    process_errors = data.process_all(self.pool, cr, conn)
    
                                    if process_errors:
                                        errors.writelines([line + '\n' for line in process_errors])
                                        
                                except Exception as e:
                                    errors.writelines('%s: %s' % (type(e), unicode(e)))
                                    
                                finally:
                                    # archive the file we processed
                                    conn.move_to_archives(file_name)
                                    
                                    # if we have errors, create txt file containing description in /errors/*.txt
                                    if errors.getvalue():
                                        errors.seek(0)
                                        conn.mkf(file_name[0:-4] + '.txt', errors, 'errors')
                                        
                                        # and upload remaining data (or unparsable file contents) to /errors/*.xml
                                        try:
                                            if data.data:
                                                conn.mkf(file_name, data.generate_xml(), 'errors')
                                        except NameError:
                                            contents = StringIO(file_contents)
                                            conn.mkf(file_name, contents, 'errors')
                                            contents.close()
                                    
                                # commit the OpenERP cursor inbetween files
                                errors.close()
                                cr and cr.commit()
                            else:
                                _logger.info(_("Could not find subclass of ads_data with file_name_prefix %s" % file_prefix))
                                conn.move_to_archives(file_name)
            finally:
                # check we are still connected, then navigate back a directory for any further operations
                if conn._connected:
                    conn.cd('..')
                else:
                    conn._connect()

        _logger.info(_("Processed %d files" % files_processed))
        return True
