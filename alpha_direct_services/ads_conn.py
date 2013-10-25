#!/usr/bin/python

from openerp.osv import osv, fields
from openerp.tools.translate import _

from ftplib import FTP
from ftplib import error_reply, error_temp, error_perm, error_proto
import socket
import StringIO
import time

from ads_data import ads_data
from ads_purchase_order import ads_purchase_order
from ads_sales_order import ads_sales_order
from ads_stock_move import ads_stock_move
from ads_product import ads_product
from ads_return import ads_return

class ads_conn(osv.osv):
    """
    Represents FTP connection to ADS server.
    Call connect and disconnect to open and close.
    Call upload_data with an ads_data object to write data to the server.
    Call poll to download and import data from ADS to OpenERP
    """

    _columns = {}
    _name = 'ads.connection'
    _auto = False

    _conn = None
    _vers_ads = 'VersADS'
    _vers_client = None

    connect_exceptions = (socket.error, IOError, error_reply, error_temp, error_perm, error_proto)

    @property
    def _connected(self):
        try:
            self._conn.voidcmd("NOOP")
            return True
        except:
            return False

    def _get_config(self, cr, config_name, value_type=str):
        """
        Get a configuration value from ir.values by config_name (For this model)
        @param str config_name: The name of the ir.values record to get
        @param object value_type: Used to cast the value to an appropriate return type.
        """
        values_obj = self.pool.get('ir.config_parameter')
        value_ids = values_obj.search(cr, 1, [('key','=',config_name)])
        if value_ids:
            value = values_obj.browse(cr, 1, value_ids[0]).value
            return value_type(value)
        else:
            return None

    def _get_ftp_config(self, cr):
        """ Save FTP connection parameters from ir.values to self """
        self._host = self._get_config(cr, 'ads_host') or 'ftp.alpha-d-s.com'
        self._port = self._get_config(cr, 'ads_port', int) or 21
        self._user = self._get_config(cr, 'ads_user') or ''
        self._password = self._get_config(cr, 'ads_password') or ''
        self._timeout = self._get_config(cr, 'ads_timeout', int) or 10
        self._mode = self._get_config(cr, 'ads_mode') or 'test'
        self._passive = self._get_config(cr, 'ads_passive', bool) or True

        message = _("Please check your ADS configuration settings in Settings -> Parameters -> System Parameters for the field '%s'")

        if not self._mode in ['prod', 'test']:
            raise osv.except_osv(_('Config Error'), _('Please check your ADS configuration settings in Settings -> Parameters -> System Parameters. Mode must be either "prod" or "test".'))
        if not self._host:
            raise osv.except_osv(_('Config Error'), message % 'host')
        if not self._user:
            raise osv.except_osv(_('Config Error'), message % 'user')
        if not self._password:
            raise osv.except_osv(_('Config Error'), message % 'password')

    def connect(self, cr):
        """ Sets up a connection to the ADS FTP server """
        if self._connected:
            self.cd('/INCONTINENCEPROTECT/%s' % self._mode)
            return self

        self._get_ftp_config(cr)
        self._conn = FTP(host=self._host, user=self._user, passwd=self._password)

        # passive on by default in python > 2.1
        if not self._passive:
            self._conn.set_pasv(self._passive)

        # change directory to self._mode, then save "VersClient" dir name
        self.cd('/INCONTINENCEPROTECT/%s' % self._mode)
        directories = self.ls()
        if len([d for d in directories if d != 'VersADS']) == 1:
            self._vers_client = [d for d in directories if d != 'VersADS'][0]
        elif 'Vers%s' % self._user in directories:
            self._vers_client = 'Vers%s' % self._user
        else:
            raise IOError('Could not find appropriate directories in %s folder.'\
                        + 'Normally there are VersADS and Vers*ClientName* directories' % self._mode)

        return self

    def disconnect(self):
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
        if not dirname:
            return False
        self._conn.cwd(dirname)

    def delete(self, filename):
        self._conn.delete(filename)

    def upload_data(self, data):
        """
        Takes an ads_data object and creates an XML file then uploads it to FTP server.
        If a file with the generated name() already exists, pause 1 second and try again.
        @param ads_data data: Contains data to be written to the file
        """
        assert isinstance(data, ads_data), 'data parameter must extend ads_data class'
        assert self._connected, 'Not connected to the FTP server'

        xml_buffer = data.generate_xml()
        self.cd(self._vers_ads)
        while True:
            if data.name() not in self.ls():
                self._conn.storlines('STOR %s' % data.name(), xml_buffer)
                break
            else:
                time.sleep(1)
        self.cd('..')

    def poll(self, cr, uid):
        """ Poll the FTP server to parse, process and then delete any data files """
        if not self._connected:
            self.connect(cr)

        # get file list from VersADS
        self.cd(self._vers_client)
        files = self.ls()

        try:
            for file_name in files:
                # get type from file name
                file_prefix = file_name.split('-', 1)[0]

                # find ads_data subclass with matching type
                class_for_type = [cls for cls in ads_data.__subclasses__() if file_prefix in cls.file_name_prefix]

                if class_for_type:
                    assert len(class_for_type) == 1, 'The following subclasses of ads_data share the file_name_prefix: %s' % class_for_type

                    # download the XML contents of the file
                    file_data = StringIO.StringIO()
                    self._conn.retrbinary('RETR %s' % file_name, file_data.write)

                    # instantiate found subclass with XML as parameter to parse it into self.data
                    file_contents = file_data.getvalue().decode("utf-8-sig").encode("utf-8")
                    data = class_for_type[0](file_contents)

                    # trigger process to import into OpenERP
                    can_delete = data.process(self.pool, cr)

                    # if process returns True, delete the file from the FTP server
                    if can_delete:
                        self.delete(file_name)
                    cr and cr.commit()
                else:
                    raise TypeError('Could not find subclass of ads_data with file_name_prefix %s' % file_prefix)
        finally:
            if self._connected:
                self.cd('..')
            else:
                self.connect(cr)
        return True
