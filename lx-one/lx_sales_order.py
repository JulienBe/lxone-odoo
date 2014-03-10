# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime
import time
from openerp.osv import osv
from openerp.tools.translate import _

from lx_data import lx_data
from tools import convert_date, parse_date
from auto_vivification import AutoVivification

class lx_sales_order(lx_data):
    """
    Handles the importation and exportation of a sales order's delivery order
    """

    file_name_prefix = ['CMDE', 'CREX']
    xml_root = 'orders'
    
    required_fields = {
        'sale_id',
        'min_date',
        'date',
    }

    def extract(self, picking_out):
        """
        Takes a stock.picking_out.out browse_record and extracts the
        appropriate data into self.data

        @param picking_out: browse_record(stock.picking.out)
        """
        picking = picking_out.pool['stock.picking'].browse(picking_out._cr, 1, picking_out.id)
        shipping_partner = picking_out.sale_id.partner_shipping_id
        invoice_partner = picking_out.sale_id.partner_invoice_id
        carrier_name = picking_out.sale_id.carrier_id and picking_out.sale_id.carrier_id.lx_ref or ''

        # Delivery method can also be added as a move line, so find all move lines whose products
        # are the delivery products of a delivery method and save IDS and lx ref for later
        carrier_move_ids = []
        if not carrier_name:
            carrier_obj = picking_out.pool['delivery.carrier']
            product_obj = picking_out.pool['product.product']

            product_ids = [move.product_id.id for move in picking_out.move_lines if move.product_id]
            carrier_map = product_obj.is_delivery_method(picking_out._cr, 1, product_ids)

            carrier_product_ids = [k for k, v in carrier_map.iteritems() if v]
            carrier_move_ids = [move.id for move in picking.move_lines if move.product_id and move.product_id.id in carrier_product_ids]

            for move in picking_out.move_lines:
                if move.id in carrier_move_ids:
                    carrier = carrier_obj.browse(picking_out._cr, 1, carrier_map[move.product_id.id][0])
                    carrier_name = carrier.lx_ref or ''

        # assert required relational fields
        assert shipping_partner.street, _('Please provide a street for the partner "%s"') % shipping_partner.name
        assert shipping_partner.city, _('Please provide a city for the partner "%s"') % shipping_partner.name
        assert shipping_partner.zip, _('Please provide a zip for the partner "%s"') % shipping_partner.name
        assert shipping_partner.country_id, _('Please provide a country for the partner "%s"') % shipping_partner.name
        
        assert invoice_partner.street, _('Please provide a street for the partner "%s"') % invoice_partner.name
        assert invoice_partner.city, _('Please provide a city for the partner "%s"') % invoice_partner.name
        assert invoice_partner.zip, _('Please provide a zip for the partner "%s"') % invoice_partner.name
        assert invoice_partner.country_id, _('Please provide a country for the partner "%s"') % invoice_partner.name
        
        self.data = AutoVivification({
            'DeliveryOrderCreate':
            {
                'DeliveryOrderHeader': {
                    'ClientOfOrder': shipping_partner.name,
                    'OrderReference': picking_out.sale_id.name,
                    'CustomerId': invoice_partner.id,
                    'Warehouse': '', # TODO
                    'ShippingType': carrier_name, 
                    'ExpectedShippingDate': parse_date(picking_out.min_date).isoformat(),
                    'ExpectedDeliveryDate': '', # TODO
                    'RegistrationTime': picking_out.date, 
                    'Remark': picking_out.id,
                    'DocumentFileNumber': picking_out.name,
                    'Addresses': {
                        'Address': [
                            {
                                'Type': 'ShipTo',
                                'PartnerId': shipping_partner.id,
                                'Name': shipping_partner.name,
                                'Street': shipping_partner.street or '',
                                'City': shipping_partner.city or '',
                                'CityZip': shipping_partner.zip,
                                'CountryCode': shipping_partner.country_id.code,
                            },
                            {
                                'Type': 'BillTo',
                                'PartnerId': invoice_partner.id,
                                'Name': invoice_partner.name,
                                'Street': invoice_partner.street or '',
                                'City': invoice_partner.city or '',
                                'CityZip': invoice_partner.zip,
                                'CountryCode': invoice_partner.country_id.code,
                            }
                        ]              
                    }, # close addresses
                    'Attributes': {
                        'Attribute': [
                            {
                                'AttributeType': 'InvoiceDoc',
                                'AttributeValue': 'SOxxxxx_Invoice.pdf',
                            },
                            {
                                'AttributeType': 'DeliveryNoteDoc',
                                'AttributeValue': 'SOxxxxx_DeliveryNote.pdf',
                            },
                        ]
                    }# close attributes
                }, # close DeliveryOrderHeader
                'DeliveryOrderLines': {
                    'DeliveryOrderLine': []                       
                }
            }, # close DeliveryOrderCreate
         })

        line_counter = 1
        for move in picking_out.move_lines:

            # skip lines that are cancelled, missing product, or product is delivery method or service
            if move.state == 'cancel' \
            or not move.product_id \
            or move.id in carrier_move_ids \
            or move.product_id.type == 'service':
                continue
            
            # assert required product information
            assert move.product_id.ean13, _('Please enter an EAN13 code for the product "%s"') % move.product_id.name

            # prepare line information
            line = {
                'LineReference': line_counter,
                'Item': {
                     'ItemAttributes': {
                         'Client': shipping_partner.name,
                         'Item': move.product_id.ean13,
                     },
                     'SerialCaptureFlag': 'No',
                     'QuantityRoundUpRule': 'EXACT',
                     'InventorizedItemFlag': 'No',
                 },
                'OrderQty': move.product_qty,
            }
            
            # add line into list of lines and increment line counter
            self.insert_data('DeliveryOrderCreate.DeliveryOrderLines.DeliveryOrderLine', line)
            line_counter += 1

        return self

    def upload(self, cr, lx_manager):
        """
        Only upload BL's with article lines. Otherwise, all articles are non-uploadable (service, delivery product), 
	so return False  so the BL can be automatically closed at sale_order.py level.
        
        Save uploaded file name to lx_file_name field.
        """
        if self.data['order']['articles']:
            res = super(lx_sales_order, self).upload(cr, lx_manager)
            if self.browse_record and self.file_name:
                self.browse_record.write({'lx_file_name': self.file_name})
            return res
        else:
            return False
        
    def _find_picking(self, cr, picking_out_obj, picking_name):
        """ Finds pickings by name. If name >= 30, use wildcard at end due to length limitations of LX1 """
        if len(picking_name) < 30:
            return picking_out_obj.search(cr, 1, [('name', '=', picking_name)])
        else:
            return picking_out_obj.search(cr, 1, [('name', 'ilike', picking_name)])

    def process(self, pool, cr, expedition):
        """
        Update picking tracking numbers / cancel picking orders
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @param AutoVivification expedition: Data from LX1 describing the expedition of the SO
        """
        # extract information
        assert 'NUM_FACTURE_BL' in expedition, 'An expedition has been skipped because it was missing a NUM_FACTURE_BL'

        picking_name = expedition['NUM_FACTURE_BL']
        status = 'STATUT' in expedition and expedition['STATUT'] or ''
        tracking_number = 'NUM_TRACKING' in expedition and expedition['NUM_TRACKING'] or ''

        # find original picking
        picking_out_obj = pool.get('stock.picking.out')
        picking_ids = self._find_picking(cr, picking_out_obj, picking_name)
        
        assert len(picking_ids) == 1, 'Found %s pickings with name %s. Should have found 1' % (len(picking_ids), picking_name)
        picking_id, = picking_ids
        picking_out = picking_out_obj.browse(cr, 1, picking_id)

        # set / append tracking number on picking
        if tracking_number:
            try:
                if picking_out.carrier_tracking_ref:
                    existing_tracking_number = picking_out.carrier_tracking_ref.split(',')
                    if str(tracking_number) not in existing_tracking_number:
                        existing_tracking_number.append(tracking_number)
                    tracking_number = ','.join(map(str, existing_tracking_number))
            except:
                pass
            picking_out_obj.write(cr, 1, picking_id, {'carrier_tracking_ref': tracking_number})

        # if status is R, order has been cancelled by LX1 because of lack of stock. We then need to
        # upload the same BL with a new name and new SO name. We handle this by cancelling BL,
        # duplicating it, confirming it then fixing the SO state from shipping_except
        if status == 'R':

            assert picking_out.state in ['assigned', 'confirmed'], \
                _("The picking %s was not in state assigned or confirmed, and therefore cannot be cancelled") % picking_name

            picking_obj = pool['stock.picking']
            picking_out_obj = pool['stock.picking.out']
            sale_order_obj = pool['sale.order']

            # get stock.picking version of stock.picking.out for access to send number field
            picking = picking_obj.browse(cr, 1, picking_out.id)
            sale = picking.sale_id

            # value for new picking's lx_send_number
            send_number = picking.lx_send_number + 1 or 1

            # Cancel original picking, then duplicate and confirm it
            picking_out_obj.action_cancel(cr, 1, [picking_id])

            # specify a name for the new BL otherwise stock module will delete the origin from it's values
            defaults = {
                'lx_send_number': send_number,
                'name': pool['ir.sequence'].get(cr, 1, 'stock.picking.out')
            }

            picking_id = picking_obj.copy(cr, 1, picking_id, defaults)
            picking_obj.signal_button_confirm(cr, 1, [picking_id])

            # fix sale order state from shipping_except to in progress
            sale_values = {}
            if sale.state == 'shipping_except':
                sale_values['state'] = 'progress'
                sale_values['shipped'] = False

                if (sale.order_policy == 'manual'):
                    for line in sale.order_line:
                        if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            sale_values['state'] = 'manual'
                            break
            if sale_values:
                sale_order_obj.write(cr, 1, sale.id, sale_values)
        return True
