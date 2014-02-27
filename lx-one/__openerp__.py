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
    'name' : 'LX-One',
    'version' : '0.1',
    'author' : 'OpenERP SA',
    'website' : 'http://www.openerp.com',
    'category' : 'Tools',
    'depends' : ['base', 'product', 'stock', 'sale', 'sale_stock', 'purchase', 'delivery'],
    'description': """
Connect OpenERP with LX-One
==========================================

Introduction
------------

This module synchronises OpenERP records with LX-One (LX1), the logistics company, by modifying workflows to upload data to LX1, and periodically polling LX1 to download updates to uploaded records. 

Key Features
------------
* Incoming Shipments are uploaded when in "Ready To Receive" state. They will then be "Received" when the polling service receives the data from LX1 
* Delivery Orders are uploaded when in "Ready to Deliver" state. They will then be "Delivered" when the polling service receives the data from LX1
* Returns are created when the polling service receives the data from LX1
* Physical Inventories are created when the polling service receives the data from LX1. Note that they are confirmed but not validated automatically.
* Full partial delivery / reception support

Configuration
-------------
Please enter your LX1 FTP server credentials in Settings > Parameters > System Parameters > lx\_*. If "mode" is set to "test" any data will not be automatically imported by LX1. Set it to "prod" to have your data automatically imported.

By default this module poles the LX1 API every 5 minutes. This interval can be changed by going to Settings > Scheduler > Scheduled Actions > Poll Alpha Direct Service Server

Technical Information
---------------------

#### Uploading

All hooks into OpenERP are kept in python files with names that match the \_name of the top most object in the workflow. For example in the Sales Order workflow, we upload the picking, but the sales\_order object is the top level object so the python file is called sales\_order.py.

All python files whose names are prefixed by "lx" and contain the name of an OE object (i.e. lx\_sales\_order.py) define how the OE object data should be extracted and uploaded to LX1. They inherit from the class lx\_data which defines certain entry points into the LX1 interaction process. 

sale\_order.py hooks into the action\_assign\_wkf method and, after various checks, instantiates an object of type lx\_sales\_order with a browse\_record to the SO's picking. The \_\_init\_\_ method of lx\_data then calls extract on itself with the browse\_record as a parameter. Extract is overridden in the lx\_sales\_order class and extracts data from the browse record, inserting it into self.data which is a dictionary based struct. sales\_order then calls "upload" on the lx\_sale\_order object.

Upload is defined by lx\_data. It gets a connection to the LX1 FTP server, then calls upload\_data on the ftp server, passing in the lx\_data child class. The lx\_connection object then calls generate\_xml on the lx\_data class which uses the pickling tools library to output XML generated from the self.data struct. This is then written to a file on the FTP server.

#### Downloading

lx\_manager.py provides a poll function that is periodically called by OE. This function gets a connection to the FTP server and gets a list of files that exist to be imported into OE.

It sorts the files based on the creation date, then by its data type (defined by the file name prefix). Next, it searches for a child class of lx\_data whose file\_name\_prefix property contains the datatype prefix of the file to process. Then, it downloads the contents of the file and instantiates an instance of the lx\_data child class with the file contents as a parameter. The \_\_init\_\_ of lx\_data converts the XML into a python dict struct with the help of the pickling tools library. 

Then it calls process\_all on the class. This is defined in lx\_data. It then loops through all root node elements passing the element to self.process which is overridden in the child class to do something with the data, for example closing a picking etc.

Finally it deletes the processed element from self.data. If any errors occur during the processing, they are stored, and the element is not deleted from self.data. At the end of the processing, if any errors have occured, a text file containing them and an XML file containing the leftover data is uploaded to the errors directory on the FTP server.

#### Summary
* lx\_connection class is a wrapper around the ftplib python class to connect to LX1 with the configuration settings in OE. It also provides some helper methods.
* lx\_manager provides a poll function that periodically connects to LX1 and downloads and processes XML files
* lx\_data is a parent class for lx\_*object\_name* classes and defines methods like upload, extract and process\_all
* lx\_*object\_name* classes extend lx\_data and override process and extract (sometimes more) methods to determine how OE should import the data from LX1

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
