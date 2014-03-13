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
    Handles the extraction of a purchase order's picking.
    """
    
    _root_node_name = None
    _header_node_name = None
    
    def process(self, pool, cr, picking):
        """
        Fully receive / delivery a picking
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @param dict picking: Data from LX1 describing the picking of the SO
        """
        # extract information
        assert self._root_node_name, '_root_node_name not set'
        assert self._header_node_name, '_header_node_name not set'
        assert 'ShipmentReference' in picking[self._root_node_name][self._header_node_name], 'Missing an order reference (DocumentFileNumber)'
        
        wizard_obj = pool.get('stock.partial.picking')
        picking_obj = pool.get('stock.picking')
        
        # get picking information and check if it is shipped
        picking_name = expedition['ShipmentReference']
        picking_id = picking_obj.search(cr, uid, [('name', '=', picking_name)])
        
        if 'DeliveryOrderStatus' in picking['DeliveryOrderCreate']['DeliveryOrderHeader']:
            status = picking['DeliveryOrderCreate']['DeliveryOrderHeader']['DeliveryOrderStatus']
            
            if status in ['SHIPPED', 'DESPATCH_CONFIRMED']:
                
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
