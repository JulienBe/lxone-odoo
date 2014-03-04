from openerp.osv import osv
from openerp.tools.translate import _

from lx_data import lx_data

class lx_test(lx_data):
    """
    Class for data importation tests
    """

    file_name_prefix = ['TEST']
    xml_root = 'TEST'

    def process(self, pool, cr, test):
        """
        Test process of data from LX1
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @param AutoVivification expedition: Data from LX1
        """
        # extract information
        assert 'body' in test, 'Need a body node!'

        # do some other stuff
        pass
    
        return 'Import successful'
