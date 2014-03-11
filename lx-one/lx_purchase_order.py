from copy import copy
import logging
_logger = logging.getLogger(__name__)

from openerp.osv import osv
from openerp.tools.translate import _

from auto_vivification import AutoVivification
from lx_data import lx_data
from tools import convert_date

class lx_purchase_order(lx_data):
    """
    Handles the extraction of a purchase order's picking.
    """

    file_name_prefix = ['FOUR']
    xml_root = 'COMMANDEFOURNISSEURS'
    _auto_remove = False
    
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
    
    def extract(self, picking):
        """
        Takes a stock.picking.in browse_record and extracts the appropriate data into self.data
        @param browse_record(stock.picking.in) picking: the stock picking browse record object
        """
        
        self.data = AutoVivification({
            'InboundShipmentCreate': {
                'InboundShipmentHeader': {
                    'ClientOfOrder': picking.partner_id.ref or picking.partner_id.name,
                    'ShipmentReference': picking.name,
                    'Warehouse': '', # TODO
                    'OrderType': 'PO',
                    'SupplierId': picking.partner_id.ref or picking.partner_id.name,
                    'Remark': picking.id,
                    'RegistrationDate': picking.date,
                    'ExpectedArrivalTime': picking.min_date,
                    'Addresses': {
                        'Address': [
                            {
                                'Type': 'ShipTo',
                                'PartnerId': picking.partner_id.ref or picking.partner_id.name,
                                'Name': picking.partner_id.name,
                                'City': picking.partner_id.city,
                                'CityZip': picking.partner_id.zip,
                                'District': picking.partner_id.country_id.code,
                            }          
                        ]
                    }                          
                },
                'InboundShipmentLines': {
                    'InboundShipmentLine': []
                }                          
            }
        })

        # iterate on move lines and use the template to create a data node that represents the PO line
        picking_line_count = 1
        for move in picking.move_lines:
            
            assert move.product_id, _("Please specify a product for all moves in picking '%s'") % picking.name
            assert move.product_id.ean13, _('Please specify an EAN13 code for the product "%s"') % move.product_id.name
            assert move.product_qty, _('Please specify a product quantity for the move "%s" on picking "%s"') % (move.name, picking.name)
            
            # construct picking line dict
            picking_line = {
                'LineReference': picking_line_count,
                'Item': {
                     'ItemAttributes': {
                         'Client': picking.partner_id.ref or picking.partner_id.name,
                         'Item': move.product_id.ean13,                   
                     }        
                },
                'ExpectedQty': move.product_qty 
            }
            
            # insert data into self.data and increment picking line count
            self.insert_data('InboundShipmentCreate.InboundShipmentLines.InboundShipmentLine', picking_line)
            picking_line_count += 1
            
        return self
