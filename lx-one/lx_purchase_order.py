from copy import copy
import logging
_logger = logging.getLogger(__name__)
from collections import OrderedDict

from openerp.osv import osv
from openerp.tools.translate import _

from lx_order import lx_order
from auto_vivification import AutoVivification
from lx_data import lx_data
from tools import convert_date

class lx_purchase_order(lx_order):
    """
    Handles the extraction of a purchase order's picking.
    """

    file_name_prefix = ['FOUR']
    message_identifier = 'OpenErpInboundShipmentCreate'
    
    required_fields = {
        'partner_id',
        'partner_id.name',
        'name',
        'date',
        'min_date',
        
        'partner_id.city',
        'partner_id.zip',
        'partner_id.country_id.code',
        
        '[move_lines].product_id',
        '[move_lines].product_id.ean13',
        '[move_lines].product_qty',
    }
    
    _root_node_name = 'InboundShipment'
    _header_node_name = 'InboundShipmentHeader'
    
    def extract(self, picking):
        """
        Takes a stock.picking.in browse_record and extracts the appropriate data into self.data
        @param browse_record(stock.picking.in) picking: the stock picking browse record object
        """
        
        self.data = OrderedDict([
            ('InboundShipmentCreate', OrderedDict([
                ('InboundShipmentHeader', OrderedDict([
                    ('ClientOfOrder', picking.partner_id.name),
                    ('ShipmentReference', picking.name),
                    ('Warehouse', ''),
                    ('OrderType', 'PO'),
                    ('SupplierId', picking.partner_id.name),
                    ('Remark', picking.note),
                    ('DocumentFileNumber', picking.origin)
                    ('RegistrationDate', picking.date),
                    ('ExpectedDepartureTime', picking.min_date),
                    ('Addresses', OrderedDict([
                        ('Address', [
                        OrderedDict([
                            ('Type', 'ShipTo'),
                            ('PartnerId', picking.partner_id.name),
                            ('Name', picking.partner_id.name),
                            ('City', picking.partner_id.city),
                            ('CityZip', picking.partner_id.zip),
                            ('District', picking.partner_id.country_id.code),
                        ])]),
                    ])),
                ])),
                ('InboundShipmentLines', OrderedDict([
                    ('InboundShipmentLine', [])                                    
                ])),
            ])),
        ])
        
        # iterate on move lines and use the template to create a data node that represents the PO line
        for move in picking.move_lines:
            
            # construct picking line dict
            picking_line = OrderedDict([
                ('LineReference', move.id),
                ('Item', OrderedDict([
                     ('ItemAttributes', OrderedDict([
                         ('Client', picking.partner_id.name),
                         ('Item', move.product_id.ean13),                   
                     ])),
                ])),
                ('ExpectedQty', move.product_qty), 
            ])
            
            # insert data into self.data and increment picking line count
            self.data['InboundShipmentCreate']['InboundShipmentLines']['InboundShipmentLine'].append(picking_line)
            
        return self
