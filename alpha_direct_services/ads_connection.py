from openerp.osv import osv
from openerp.tools.translate import _

from ftplib import FTP
from ftplib import error_reply, error_temp, error_perm, error_proto, all_errors
import time

from ads_data import ads_data

class ads_connection(object):
    """
    Wraps an FTP connection to the ADS server and provides some helper methods
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
        self._disconnect()

    @property
    def _connected(self):
        try:
            self._ping()
            return True
        except all_errors:
            return False

    def _ping(self):
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
        self._mode = self._get_config('ads_mode') or 'test'
        self._passive = self._get_config('ads_passive', bool) or True

        message = _("Please check your ADS configuration settings in Settings -> Parameters -> System Parameters for the field '%s'")

        if not self._mode in ['prod', 'test']:
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

    def _disconnect(self):
        """ Closes a previously opened connection to the ADS FTP server """
        if self._connected:
            self._conn.quit()

    # ftp convenience methods
    def ls(self):
        if hasattr(self._conn, 'mlst'):
            return self._conn.mlsd()
        else:
            return self._conn.nlst()

    def cd(self, dirname):
        if dirname:
            self._conn.cwd(dirname)

    def try_cd(self, dirname):
        try:
            self.cd(dirname)
        except all_errors as e:
            pass

    def mkd(self, dirname):
        if dirname:
            self._conn.mkd(dirname)

    def rename(self, old_name, new_name):
        self._conn.rename(old_name, new_name)

    def archive(self, filename):
        if 'archives' not in self.ls():
            self.mkd('archives')
        self.rename(filename, 'archives/%s' % filename)

    def delete(self, filename):
        self.archive(filename)
        
    def upload_data(self, data):
        """
        Takes an ads_data object and creates an XML file then uploads it to FTP server.
        If a file with the generated name() already exists, pause 1 second and try again.
        @param ads_data data: Contains data to be written to the file
        """
        assert isinstance(data, ads_data), 'data parameter must extend ads_data class'
        if not self._connected:
            self._connect()

        self.cd(self._vers_ads)

        try:
            xml_buffer = data.generate_xml()
            while True:
                if data.name() not in self.ls():
                    self._conn.storlines('STOR %s' % data.name(), xml_buffer)
                    break
                else:
                    time.sleep(1)

        finally:
            self.try_cd('..')
