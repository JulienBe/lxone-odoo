# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime
import time
from collections import OrderedDict

from openerp.osv import osv
from openerp.tools.translate import _

from lx_order import lx_order
from lx_data import lx_data
from tools import convert_date, parse_date
from auto_vivification import AutoVivification

class lx_sales_order(lx_order):
    """
    Handles the importation and exportation of a sales order's delivery order
    """

    object_type = ['OpenErpOutboundShipment']
    message_identifier = 'OpenErpDeliveryOrderCreate' 
    
    required_fields = {
        'sale_id',
        'min_date',
        'date',
        
        'sale_id.partner_shipping_id.street',
        'sale_id.partner_shipping_id.city',
        'sale_id.partner_shipping_id.zip',
        'sale_id.partner_shipping_id.country_id',
        'sale_id.partner_invoice_id.street',
        'sale_id.partner_invoice_id.city',
        'sale_id.partner_invoice_id.zip',
        'sale_id.partner_invoice_id.country_id',
        
        '[move_lines].product_id',
        '[move_lines].product_id.ean13',
        '[move_lines].product_qty',
    }
    
    _header_node_name = 'OutboundShipmentHeader'
    _statuses_to_process = ['IN_TRANSIT', 'RECEIVED', 'CONFIRMED']

    def extract(self, picking_out):
        """
        Takes a stock.picking_out.out browse_record and extracts the
        appropriate data into self.data

        @param picking_out: browse_record(stock.picking.out)
        """
        pool = picking_out.pool
        cr = picking_out._cr
        uid = 1
        
        picking = pool['stock.picking'].browse(cr, 1, picking_out.id)
        shipping_partner = picking_out.sale_id.partner_shipping_id
        invoice_partner = picking_out.sale_id.partner_invoice_id
        carrier_name = picking_out.sale_id.carrier_id and picking_out.sale_id.carrier_id.lx_ref or ''
    
        # Delivery method can also be added as a move line, so find all move lines whose products
        # are the delivery products of a delivery method and save IDS and lx ref for later
        carrier_move_ids = []
        if not carrier_name:
            carrier_obj = pool['delivery.carrier']
            product_obj = pool['product.product']

            product_ids = [move.product_id.id for move in picking_out.move_lines if move.product_id]
            carrier_map = product_obj.is_delivery_method(cr, uid, product_ids)

            carrier_product_ids = [k for k, v in carrier_map.iteritems() if v]
            carrier_move_ids = [move.id for move in picking.move_lines if move.product_id and move.product_id.id in carrier_product_ids]

            for move in picking_out.move_lines:
                if move.id in carrier_move_ids:
                    carrier = carrier_obj.browse(cr, uid, carrier_map[move.product_id.id][0])
                    carrier_name = carrier.lx_ref or ''
        
        # generate invoice reports 
        if not all([invoice.state in ['open', 'paid'] for invoice in picking.sale_id.invoice_ids]):
            raise osv.except_osv(_('Invoice is Draft'), _('Picking "%s" has an invoice in draft state. All invoices belonging to this picking must be validated before processing.') % picking.name)

        self.add_attachments(pool, cr, uid, 'account.invoice', [invoice.id for invoice in picking.sale_id.invoice_ids],\
                              'account.invoice', picking.name + '_invoice', 'InvoiceDoc')
        
        # generate delivery slip
        self.add_attachments(pool, cr, uid, 'stock.picking.out', [picking.id], 'stock.picking.list.out', picking.name + '_delivery', 'DeliverySlip')

        # extract browse_record into self.data        
        self.data = OrderedDict([
            ('DeliveryOrderCreate', OrderedDict([
                ('DeliveryOrderHeader', OrderedDict([
                    ('ClientOfOrder', 'FW9'),
                    ('OrderReference', picking_out.sale_id.name),
                    ('Warehouse', 'GAR'),
                    ('CustomerId', invoice_partner.id),
                    ('ShippingType', carrier_name),
                    ('ExpectedDeliveryDate', parse_date(picking_out.min_date).isoformat()),
                    ('Remark', picking_out.note or ''),
                    ('DocumentFileNumber', picking_out.name),
                    ('Addresses', OrderedDict([
                        ('Address', [OrderedDict([
                            ('Type', 'ShipTo'),
                            ('PartnerId', shipping_partner.name),
                            ('Name', shipping_partner.name),
                            ('Street', shipping_partner.street or ''),
                            ('City', shipping_partner.city or ''),
                            ('CityZip', shipping_partner.zip),
                            ('CountryCode', shipping_partner.country_id.code),
                        ]),
                        OrderedDict([
                            ('Type', 'BillTo'),
                            ('PartnerId', invoice_partner.name),
                            ('Name', invoice_partner.name),
                            ('Street', invoice_partner.street or ''),
                            ('City', invoice_partner.city or ''),
                            ('CityZip', invoice_partner.zip),
                            ('CountryCode', invoice_partner.country_id.code),
                        ])]),
                    ])),
                    ('Attributes', OrderedDict([
                        ('Attribute', []),
                    ])),
                ])),
                ('DeliveryOrderLines', OrderedDict([
                    ('DeliveryOrderLine', [])                                    
                ])),
            ])),
        ])
        
        # fill attachments
        for content, name, extension, type in self._attachments:
            attachment = OrderedDict([
                            ('AttributeType', type),
                            ('AttributeValue', '%s.%s' % (name, extension)),
                         ])
            self.data['DeliveryOrderCreate']['DeliveryOrderHeader']['Attributes']['Attribute'].append(attachment)
            
        for move in picking_out.move_lines:

            # skip lines that are cancelled, missing product, or product is delivery method or service
            if move.state == 'cancel' \
            or not move.product_id \
            or move.id in carrier_move_ids \
            or move.product_id.type == 'service':
                continue
            
            # prepare line information
            line = OrderedDict([
                ('LineReference', move.id),
                ('Item', OrderedDict([
                     ('ItemAttributes', OrderedDict([
                         ('Client', 'FW9'),
                         ('Item', move.product_id.ean13),
                     ])),
                     ('SerialCaptureFlag', 'No'),
                     ('QuantityRoundUpRule', 'EXACT'),
                     ('InventorizedItemFlag', 'No'),
                 ])),
                ('OrderQty', move.product_qty),
            ])
            
            # add line into list of lines and increment line counter
            self.data['DeliveryOrderCreate']['DeliveryOrderLines']['DeliveryOrderLine'].append(line)

        return self
