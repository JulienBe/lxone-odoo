from openerp.osv import osv
from openerp.tools.translate import _

from StringIO import StringIO
from ftplib import FTP
from ftplib import error_reply, error_temp, error_perm, error_proto, all_errors
import time

from ads_data import ads_data

def ensure_connection(function):
    """ Check we are connected before calling a function, and connect if necessary """
    def inner(self, *args, **kwargs):
        if not self._connected:
            self._connect()
        
        return function(self, *args, **kwargs)
    return inner

class ads_connection(object):
    """
    Wraps an FTP connection to the ADS server and provides some helper methods.
    Use it with the python using construct, and by passing in a pool and cr to the
    constructor.
    """

    def __init__(self, pool, cr):
        """
        Set up the FTP connection
        @param pool: OpenERP object pool
        @param cr: OpenERP cursor object
        """
        super(ads_connection, self).__init__()

        self._pool = pool
        self._cr = cr

        self._conn = None
        self._vers_ads = 'VersADS'
        self._vers_client = None

    def __enter__(self):
        """ Allows python 'using' construct"""
        try:
            self._connect()
        except all_errors as e:
            raise osv.except_osv(_("Connection Problem"), \
                    _("".join(["There was a problem connecting to the ADS servers.\n\n",
                               "Please check your connection settings in ",
                               "Setings > Parameters > System Parameters and make sure ",
                               "your IP is in the ADS FTP whitelist.\n\n",
                               "%s""" % unicode(e)])))
        return self

    def __exit__(self, type, value, traceback):
        """ Allows python 'using' construct"""
        self._disconnect()

    @property
    def _connected(self):
        """ Pings the server to determine if we are still connected """
        try:
            self._ping()
            return True
        except all_errors:
            return False

    def _ping(self):
        """ Pings the server to determine if we are still connected """
        self._conn.voidcmd("NOOP")

    def _get_config(self, config_name, value_type=str):
        """
        Get a configuration value from ir.values by config_name (For this model)
        @param str config_name: The name of the ir.values record to get
        @param object value_type: Used to cast the value to an appropriate return type.
        """
        values_obj = self._pool.get('ir.config_parameter')
        value_ids = values_obj.search(self._cr, 1, [('key','=',config_name)])
        if value_ids:
            value = values_obj.browse(self._cr, 1, value_ids[0]).value
            return value_type(value)
        else:
            return None

    def _get_ftp_config(self):
        """ Save FTP connection parameters from ir.values to self """
        self._host = self._get_config('ads_host') or 'ftp.alpha-d-s.com'
        self._port = self._get_config('ads_port', int) or 21
        self._user = self._get_config('ads_user') or ''
        self._password = self._get_config('ads_password') or ''
        self._timeout = self._get_config('ads_timeout', int) or 10
        self._mode = self._get_config('ads_mode').upper() or 'TEST'
        self._passive = self._get_config('ads_passive', bool) or True

        message = _("Please check your ADS configuration settings in Settings -> Parameters -> System Parameters for the field '%s'")

        if not self._mode in ['PROD', 'TEST']:
            raise osv.except_osv(_('Config Error'), _('Please check your ADS configuration settings in Settings -> Parameters -> System Parameters. Mode must be either "prod" or "test".'))
        if not self._host:
            raise osv.except_osv(_('Config Error'), message % 'host')
        if not self._user:
            raise osv.except_osv(_('Config Error'), message % 'user')
        if not self._password:
            raise osv.except_osv(_('Config Error'), message % 'password')

    def _connect(self):
        """ Sets up a connection to the ADS FTP server """
        self._get_ftp_config()
        self._conn = FTP(host=self._host, user=self._user, passwd=self._password)

        # passive on by default in python > 2.1
        if not self._passive:
            self._conn.set_pasv(self._passive)

        # change directory to self._mode, then save "VersClient" dir name
        self.cd(self._mode)
        
        # get name of VersClient directory
        directories = self.ls()
        vers_client_dir = filter(lambda direc: direc[0:4] == 'Vers' and direc != 'VersADS', directories)

        if len(vers_client_dir) == 1:
            self._vers_client = vers_client_dir[0]
        elif 'Vers%s' % self._user in directories:
            self._vers_client = 'Vers%s' % self._user
        else:
            raise IOError('Could not find appropriate directories in %s folder.'\
                        + 'Normally there are VersADS and Vers*ClientName* directories' % self._mode)
            
        # safety check for production mode. If VersClient dir contains file "misc/database_name.txt", require
        # the database name inside to be the same as this database name. This helps to prevent 
        # the situation where somebody backs up and restores a db locally and forgets to change to mode test
        if self._mode == 'PROD':
            self.cd(self._vers_client)
            directories = self.ls()
            if 'security' in directories:
                self.cd('security')
                files = self.ls()
                if 'database_name.txt' in files:
                    database_name = self.download_data('database_name.txt').strip()
                    if not database_name == self._cr.dbname:
                        self.cd('../../')
                        self._disconnect()
                        raise osv.except_osv(_("Production Warning"), "The ADS module is still in production mode and your database name (%s) does not match the database name in the file 'security/database_name.txt' (%s).\n\nPlease either change your ads_mode or the database name in the text file." % (self._cr.dbname, database_name))
                self.cd('..')
            self.cd('..')

    def _disconnect(self):
        """ Closes a previously opened connection to the ADS FTP server """
        if self._connected:
            self._conn.quit()
            
    def outer(some_func):
         def inner():
             print "before some_func"
             ret = some_func() # 1
             return ret + 1
         return inner

    # ftp convenience methods
    def ls(self):
        """ List files and directories in the current directory """
        if hasattr(self._conn, 'mlst'):
            return self._conn.mlsd()
        else:
            return self._conn.nlst()

    def cd(self, dirname):
        """ change working directory """
        if dirname:
            self._conn.cwd(dirname)

    def try_cd(self, dirname):
        """ change working directory. Silently catch FTP errors """
        try:
            self.cd(dirname)
        except all_errors as e:
            pass

    def mkd(self, dirname):
        """ Create directory in the current working directory """
        if dirname:
            self._conn.mkd(dirname)

    def mkf(self, filename, contents, directory=None):
        """ 
        Create a file with filename and contents in the current or specified directory
        @param buffer contents: Buffer object like StringIO containing contents
        """
        self._conn.storlines('STOR %s%s' % (directory and directory + '/' or '', filename), contents)

    def rename(self, old_name, new_name, add_postfix_if_exists=True):
        """ rename / move a file """
        try:
            self._conn.rename(old_name, new_name)
        except error_perm as e:
            if 'existant' in e.message:
                new_name = new_name.split('.')
                new_name = "-new.".join(new_name)
                self.rename(old_name, new_name)
            else:
                raise

    def move_to_archives(self, filename):
        """ move specified file to the 'archives' folder (automatically created) """
        if 'archives' not in self.ls():
            self.mkd('archives')
        self.rename(filename, 'archives/%s' % filename)

    def move_to_errors(self, filename):
        """ move specified file to the 'errors' folder (automatically created) """
        if 'errors' not in self.ls():
            self.mkd('errors')
        self.rename(filename, 'errors')
        
    def rm(self, filename):
        """ Delete a file """
        return self._conn.delete(filename)
        
    @ensure_connection
    def download_data(self, file_name):
        """ 
        Downloads data for the specified file 
        @return str the contents of the file
        """
        data = StringIO()
        self._conn.retrbinary('RETR %s' % file_name, data.write)
        contents = data.getvalue()
        data.close()
        return contents

    @ensure_connection
    def upload_data(self, data, copy_to_archive=True):
        """
        Generates an XML file from an ads_data subclass, then generates a name for the file
        and checks if it exists on the server. If it does, wait .1 second and generate again.
        It will then upload the file to the server and if copy_to_archive is true, it will
        upload the same file to the archive directory.
        @param ads_data data: Contains data to be written to the file
        @param bool copy_to_archive: If true, the same file will also be uploaded to the archive directory
        """
        assert isinstance(data, ads_data), 'data parameter must extend ads_data class'
        
        self.cd(self._vers_ads)

        try:
            xml_buffer = data.generate_xml()

            while True:
                name = data.name()
                files = self.ls()
                
                if name not in files:
                    self.mkf(name, xml_buffer)
                    
                    # upload a copy to archive directory
                    if copy_to_archive:
                        if 'archives' not in files:
                            self.mkd('archives')
                        xml_buffer.seek(0)
                        self.mkf(name, xml_buffer, 'archives')
                        
                    break
                else:
                    time.sleep(0.1)

        finally:
            self.try_cd('..')
            
        return name

    @ensure_connection            
    def delete_data(self, file_name):
        """
        Deletes the file (and archive) with name file_name. Throws ftplib.error_perm(500) if not found
        @param string file_name: The name of the file to try to delete
        """
        self.cd(self._vers_ads)

        try:
            # delete original file
            self.rm(file_name)
            
            # no exception, so go on to delete archive
            self.cd('archives')
            files = self.ls()
            if file_name in files:
                self.rm(file_name)
            self.cd('..')
            
        finally:
            self.try_cd('..')
            
        return True
