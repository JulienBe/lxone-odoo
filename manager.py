from openerp.osv import osv
from openerp.tools.translate import _
from openerp import pooler

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

lx_classes = [
    lx_purchase_order,
    lx_sales_order,
    lx_product,
    lx_return,
    lx_stock,
    lx_picking
]

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
    
    def thread_lock(function):
        """ Aquire a thread lock before calling the function and release it afterwards """
        
        def inner(self, *args, **kwargs):
            if not self._lock.acquire(False):
                raise osv.except_osv(_('Already Syncing'), _('We are already synchronizing with LX1. Please wait a moment before trying again...'))
            
            try:
                res = function(self, *args, **kwargs)
            except:
                raise
            finally:
                self._lock.release()
            return res
        
        return inner

    def connection(self, cr):
        """ Gets an instance of lx_connection class that wraps the FTP server """
        return lx_connection(self.pool, cr)

    @thread_lock
    def poll(self, cr, uid=1):
        """
        Poll the LX1 FTP server, download a file list and iterate over them by oldest first by 
        file sequence number. For each file, download the contents and create a lx.file.incoming 
        record, committing cursor in between files.
        """
        
        files_processed = 0
        sync_id = False
        file_incoming_obj = self.pool.get('lx.file.incoming')
        sync_obj = self.pool.get('lx.sync')
        
        # get connection to FTP server
        with self.connection(cr) as conn:

            # get list of files and directories and remove any files that cannot be processed
            # then order files by file_sequence so they are processed in the correct order
            files_and_directories = conn.ls()
            files_and_directories = filter(lambda f: '.' in f, files_and_directories)
            files_to_process = map(lambda f: lx_file(f), files_and_directories)
            files_to_process = filter(lambda f: f.valid, files_to_process)
            files_to_process = filter(lambda f: f.to_process(), files_to_process)
            files_to_process.sort(key=lambda f: f.file_sequence)
            
            # return if there are no files to process
            if not files_to_process:
                return sync_id
            
            # Prepare values for lx.sync record
            sync_vals = {
                'date': datetime.now(), 
                'log': [],
            }
            sync_id = sync_obj.create(cr, uid, sync_vals)
            cr.commit()
            new_cursor = False

            # Process files within try catch block and append errors to sync_vals
            try:
                for file_to_process in files_to_process:

                    files_processed += 1
                    file_name = file_to_process.file_name
                    activity = 'processing file'

                    # download file contents and create lx.file.incoming from it, then save ID in sync_vals                    
                    try:
                        activity = 'creating lx.file.incoming'
                        file_contents = conn.download_data(file_name)
                        
                        # Convert latin encoding to utf
                        file_contents = file_contents.decode('ISO-8859-1')
                        
                        vals = {
							'xml_file_name': file_name,
                            'xml': file_contents,
                            'sync_id': sync_id,
                        }
                        file_incoming_id = file_incoming_obj.create(cr, uid, vals)
                        
                        # delete the file we successfully processed
                        activity = 'deleting file from ftp server'
                        conn.rm(file_name)

                    except Exception as e:
                        sync_vals['log'].append('Error while %s for %s: %s' % (activity, file_name, unicode(e)))
                        files_processed -= 1
                        cr = pooler.get_db(cr.dbname).cursor()
                        new_cursor = True
                        
                    finally:
                        # commit the OpenERP cursor inbetween files
                        cr.commit()
                        
            finally:
                # update the sync log
                sync_obj.write(cr, uid, [sync_id], sync_vals)
                cr.commit()
                if new_cursor:
                    cr.close()
                
        # * end with conn * #
        
        try:
            # trigger parse all files
            activity = 'parsing all files'
            file_incoming_obj.parse_all(cr, uid)
            
            # trigger creation of all lx.updates for files
            activity = 'generating all updates'
            file_incoming_obj.generate_all_updates(cr, uid)
            
            # trigger execution of all lx.updates for files
            activity = 'executing all updates'
            file_incoming_obj.execute_all_updates(cr, uid)
            
        except Exception as e:
            sync_vals['log'].append('Error while %s: %s' % (activity, unicode(e)))
        
        # update lx.sync record
        sync_obj.write(cr, uid, [sync_id], sync_vals)

        return sync_id

def get_lx_data_subclass(object_type):
    """ Finds a subclass of lx_data whose object_type matches @param object_type """
    class_for_data_type = [cls for cls in lx_classes if object_type in cls.object_type]
    assert len(class_for_data_type) == 1, _('Should have found 1 class for data type %s' % object_type)
    return class_for_data_type[0]
