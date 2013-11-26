# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name' : 'Alpha Direct Services',
    'version' : '1.0',
    'author' : 'OpenERP SA',
    'website' : 'http://www.openerp.com',
    'category' : 'Tools',
    'depends' : ['base', 'product', 'stock', 'sale', 'sale_stock', 'purchase', 'delivery'],
    'description': """
Connect OpenERP with Alpha Direct Services
==========================================

This module synchronises OpenERP records with Alpha Direct Services (ADS), the logistics company, by modifying workflows to upload data to ADS, and periodically polling ADS to download updates to uploaded records. 

Key Features
------------
* Incoming Shipments are uploaded when in "Ready To Receive" state. They will then be "Received" when the polling service receives the data from ADS 
* Delivery Orders are uploaded when in "Ready to Deliver" state. They will then be "Delivered" when the polling service receives the data from ADS
* Returns are created when the polling service receives the data from ADS
* Physical Inventories are created when the polling service receives the data from ADS. Note that they are confirmed but not validated automatically.

Configuration
-------------
Please enter your ADS FTP server credentials in Settings > Parameters > System Parameters > ads_*. If "mode" is set to "test" any data will not be automatically imported by ADS. Set it to "prod" to have your data automatically imported.

By default this module poles the ADS API every 5 minutes. This interval can be changed by going to Settings > Scheduler > Scheduled Actions > Poll Alpha Direct Service Server

Notes
-----
This module uses the PicklingTools library:
http://www.picklingtools.com/
    """,
    'data': [
        'data/config.xml',
        'data/cron.xml',
        'views/stock_picking_in_form.xml',
        'views/res_partner_form.xml',
        'views/stock_picking_out_form.xml',
        'views/product_form.xml',
        'views/delivery_carrier_form.xml',
    ],
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
