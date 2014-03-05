from openerp.osv import osv
from openerp.tools.translate import _

from ftplib import all_errors
from StringIO import StringIO
from datetime import datetime
from threading import Lock

from connection import lx_connection
from auto_vivification import AutoVivification
from file import lx_file

from lx_data import lx_data
from lx_purchase_order import lx_purchase_order
from lx_sales_order import lx_sales_order
from lx_product import lx_product
from lx_return import lx_return
from lx_stock import lx_stock
from lx_picking import lx_picking
from lx_test import lx_test

class lx_manager(osv.osv):
    """
    Instantiates an FTP connection wrapper object and allows polling the LX1 FTP Server
    """

    _columns = {}
    _name = 'lx.manager'
    _auto = False
    _lock = Lock()

    _file_process_order = [
        'MVTS',# PO received
        'CREX',# SO sent
        'CRET',# return
        'STOC',# physical inventory
        'TEST',
    ]

    ftp_exceptions = all_errors

    def connection(self, cr):
        """ Gets an instance of lx_connection class that wraps the FTP server """
        return lx_connection(self.pool, cr)

    def poll(self, cr, uid=1):
        """
        Poll the LX1 FTP server, download a file list and iterate over them by oldest first by 
        file sequence number. For each file, download the contents and create a lx.update.file 
        record, committing cursor in between files.
        """
        # setup thread locking
        if not self._lock.acquire(False):
            raise osv.except_osv(_('Already Syncing'), _('We are already synchronizing with LX1. Please wait a while before trying again...'))

        files_processed = 0
        sync_id = False
        update_file_obj = self.pool.get('lx.update.file')
        sync_obj = self.pool.get('lx.sync')
        
        # get connection to FTP server
        with self.connection(cr) as conn:

            conn.cd(conn._vers_client)

            # get list of files and directories and remove any files that cannot be processed
            # then order files by file_sequence so they are processed in the correct order
            files_and_directories = conn.ls()
            files_to_process = map(lambda f: lx_file(f), files_and_directories)
            files_to_process = filter(lambda f: f.valid, files_to_process)
            files_to_process = filter(lambda f: f.to_process(), files_to_process)
            files_to_process.sort(key=lambda f: f.file_sequence)
            
            # return if there are no files to process
            if not files_to_process:
                self._lock.release()
                return sync_id
            
            # Prepare values for lx.sync record
            sync_vals = {
                'date': datetime.now(), 
                'log': [],
            }
            sync_id = sync_obj.create(cr, uid, sync_vals)

            # Process files within try catch block and append errors to sync_vals
            try:
                for file_to_process in files_to_process:

                    files_processed += 1
                    file_name = file_to_process.file_name
                    activity = 'processing file'

                    # download file contents and create lx.update.file from it, then save ID in sync_vals                    
                    try:
                        activity = 'creating lx.update.file'
                        file_contents = conn.download_data(file_name)
                        vals = {
                            'xml': file_contents,
                            'file_name': file_name,
                            'sync_id': sync_id,
                        }
                        update_file_id = update_file_obj.create(cr, uid, vals)
                        
                        # delete the file we successfully processed
                        activity = 'deleting file from ftp server'
                        conn.rm(file_name)

                    except Exception as e:
                        sync_vals['log'].append('Error while %s for %s: %s' % (activity, file_name, unicode(e)))
                        files_processed -= 1
                        
                    finally:
                        # commit the OpenERP cursor inbetween files
                        cr and cr.commit()
                        
            finally:
                # check we are still connected, then navigate back a directory for any further operations
                if conn._connected:
                    conn.cd('..')
                else:
                    conn._connect()

        # * end with conn * #
        
        try:
            # trigger parse all files
            activity = 'parsing all files'
            update_file_obj.parse_all(cr, uid)
            
            # trigger creation of all lx.update.nodes for files
            activity = 'generating all updates'
            update_file_obj.generate_all_update_nodes(cr, uid)
            
            # trigger execution of all lx.update.nodes for files
            activity = 'executing all update nodes'
            update_file_obj.execute_all_update_nodes(cr, uid)
            
        except Exception as e:
            sync_vals['log'].append('Error while %s: %s' % (activity, unicode(e)))
        
        # update lx.sync record
        sync_obj.write(cr, uid, [sync_id], sync_vals)
        
        # release thread lock
        self._lock.release()

        return sync_id
