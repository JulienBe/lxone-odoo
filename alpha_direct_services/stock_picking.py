#!/usr/bin/python

from copy import copy
from openerp.osv import osv, fields

class stock_picking(osv.osv):
    """ Inherit the stock.picking object to and add ads_sent and ads_result fields """
    
    _inherit = 'stock.picking'
    _columns = {
        'ads_sent': fields.boolean('Sent to ADS?', help="This field indicates whether or not this document has been uploaded to Alpha Direct Systems for processing."),
        'ads_result': fields.text('ADS Send Results', help="If there are any errors while sending this document to ADS, they will be logged here"),
    }

class stock_picking_in(osv.osv):
    """ Inherit the stock.picking.in object to and add ads_sent and ads_result fields """

    _inherit = 'stock.picking.in'
    _columns = {
        'ads_sent': fields.boolean('Sent to ADS?', help="This field indicates whether or not this document has been uploaded to Alpha Direct Systems for processing."),
        'ads_result': fields.text('ADS Send Results', help="If there are any errors while sending this document to ADS, they will be logged here"),
    }
