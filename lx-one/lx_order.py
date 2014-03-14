from copy import copy
import logging
_logger = logging.getLogger(__name__)
from collections import OrderedDict

from openerp.osv import osv
from openerp.tools.translate import _

from auto_vivification import AutoVivification
from lx_data import lx_data
from tools import convert_date

class lx_order(lx_data):
    """
    Implements the process method to handle purchase or sale order pickings in a generic way.
    Tune behaviour for purchase or sales order by changing the self._* variables in child class
    """
    
    _header_node_name = None
    _statuses_to_process = None
    
    def process(self, pool, cr):
        """
        Fully receive / delivery a picking
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @param dict picking: Data from LX1 describing the picking of the SO
        """
        # extract information
        assert self._header_node_name, '_header_node_name not set'
        assert self._statuses_to_process, '_statuses_to_process not set'
        assert 'Status' in self.data[self._header_node_name], 'Missing an order reference (DocumentFileNumber)'
        
        wizard_obj = pool.get('stock.partial.picking')
        picking_obj = pool.get('stock.picking')
        
        # get picking information and check if it is shipped
        picking_name = self.data[self._header_node_name]['ShipmentReference']
        picking_id = picking_obj.search(cr, 1, [('name', '=', picking_name)])
        assert picking_id, _("Could not find picking with name '%s'") % picking_name
        
        # receive / deliver picking based on status from LX1
        status = self.data[self._header_node_name]['Status']
        if status in self._statuses_to_process:
            
            # mark picking as delivered
            context = {
                'active_model': 'stock.picking',
                'active_ids': picking_id,
                'active_id': picking_id[0],
            }
            
            wizard_id = wizard_obj.create(cr, 1, {}, context=context)
            wizard_obj.do_partial(cr, 1, [wizard_id])
            
        else:
            pass # do nothing as picking is not shipped yet
