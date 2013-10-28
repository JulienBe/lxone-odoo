import logging
_logger = logging.getLogger(__name__)
from openerp.osv import osv
from openerp.tools.translate import _

from ftplib import all_errors
from StringIO import StringIO

from ads_connection import ads_connection
from ads_data import ads_data
from ads_purchase_order import ads_purchase_order
from ads_sales_order import ads_sales_order
from ads_stock_move import ads_stock_move
from ads_product import ads_product
from ads_return import ads_return

class ads_manager(osv.osv):
    """
    Instantiates an FTP connection wrapper object and allows polling the ADS FTP Server
    """

    _columns = {}
    _name = 'ads.manager'
    _auto = False

    ftp_exceptions = all_errors

    def connection(self, cr):
        """ Gets an instance of ads_connection class that wraps the FTP server """
        return ads_connection(self.pool, cr)

    def poll(self, cr, uid=1):
        """ Poll the FTP server to parse, process and then archive any data files """

        _logger.info(_("Polling ADS Server..."))
        files_processed = 0
        
        # get connection FTP server
        with self.connection(cr) as conn:

            # get list of files and directories
            conn.cd(conn._vers_client)
            files_and_directories = conn.ls()
            files_to_process = [f for f in files_and_directories if '.' in f]

            try:
                # create archive directory if doesn't already exist
                if 'archives' not in files_and_directories:
                    conn.mkd('archives')

                # loop over files and process them
                for file_name in files_to_process:
                    files_processed += 1

                    # get data type from the file name
                    file_prefix = file_name.split('-', 1)[0]

                    # find ads_data subclass with matching 'type' property
                    class_for_data_type = [cls for cls in ads_data.__subclasses__() if file_prefix in cls.file_name_prefix]

                    if class_for_data_type:

                        # log warning if found more than one matching class
                        if len(class_for_data_type) != 1:
                            _logger.warn(_('The following subclasses of ads_data share the file_name_prefix: %s' % class_for_data_type))

                        # download the XML contents of the file
                        file_data = StringIO()
                        conn._conn.retrbinary('RETR %s' % file_name, file_data.write)

                        # instantiate found subclass with correctly encoded file_data
                        file_contents = file_data.getvalue().decode("utf-8-sig").encode("utf-8")
                        data = class_for_data_type[0](file_contents)

                        # trigger process to import into OpenERP
                        can_archive = data.process(self.pool, cr)

                        # if process returns True, archive the file from the FTP server
                        if can_archive:
                            conn.archive(file_name)

                        # commit the OpenERP cursor inbetween files
                        cr and cr.commit()
                    else:
                        _logger.info(_("Could not find subclass of ads_data with file_name_prefix %s" % file_prefix))
                        conn.archive(file_name)
            finally:
                # check we are still connected, then navigate back a directory for any further operations
                if conn._connected:
                    conn.cd('..')
                else:
                    conn._connect(cr)

        _logger.info(_("Processed %d files" % files_processed))
        return True
