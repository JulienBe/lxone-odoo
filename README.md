# Introduction

This module integrates Odoo (v8) with the LX1 logistics system to synchronise Delivery Orders, Incoming Shipments, Returns, Products and Physical Inventories between the two systems. The data delivery method is by XML files uploaded and downloaded to and from an FTP server hosted by PVS (The proprietor of the LX1 system).

# Inner Workings

## Uploading Data

This section concerns the uploading of data from Odoo to LX1, for example sending new Delivery Orders or updating product information in LX1. In order to acheive this, the module is split into 3 parts:

### Hooks

The hooks are the main entry point of this module. They are used to define events in Odoo that should trigger the synchronisation of a related object. For example, when a user writes some new values to a product, that product should be uploaded. This is acheived by the oe_product.py file in the hooks directory overriding the write field and calling self.upload (Note that this method is provided by having the product.product class inherit from oe_lx). 

The upload method takes a cursor, uid, single or a list of browse records, and finally a subclass of the lx_data class defined in the serialization folder.

### Serialization

The serializtion folder contains the python files that extract one or many browse records into OrderedDict's so that their data can be serialized into XML and uploaded to the FTP server. 

The lx_data class is the parent class to use when creating a new class to perform the data extraction from an Odoo record. It defines several variables and methods that should be set and overridden by the child class to implement the serialization mechanism. 

We can use the lx_product.py file in the serialization folder as an example of product.product serialization. 

- The object_type field is used to identify the type of data carried by the resulting XML file. 
- The message_identifier is the name of the type of message that this XML file represents, and will be injected into a standard XML header element. 
- The required_fields property defines fields on the browse_record that should be truthy, otherwise an exception is raised when trying to upload. 
- Finally the extract method should extract data from the parameter "products" browse record or list of browse records and place it in OrderedDict's in self.data.

Upon the instantiation of a class that inherits lx_data, self.extract is called with the browse record parameter and the data is extracted into the data variable of the lx_data subclass. You can then call generate_xml to convert the OrderedDict in the data variable to XML to be uploaded to the FTP server. 

This whole process is abstracted into the upload function of the oe_lx class which should be called directly in the hook python file. 

### Uploading

When uploading to the FTP server, a file.outgoing record is created with the XML data in it's values. We then attempt to upload the data as an XML file to the FTP server. Any errors that occur at this point are saved on the file.outgoing record. This object helps us better recover from errors and lets us keep an audit trail of the files moving to and from the FTP server.

When we attempt an upload of a file.outgoing record, we call it's upload function. This uses the lx_manager class to establish a connection with the FTP server using the lx_connection class that provides a layer of abstraction over the python ftplib module. The FTP connection details are saved in the ir.config_parameter model and are accessible through the LX1 menu in the Odoo backend. 

While a connection is established on the FTP server a thread lock is employed to block other processes from interacting with the FTP server at the same time, in order to maintain the integrity of the data. 

## Downloading Data

This section covers downloading data from the LX1 system, for example being notified of the delivery of a Delivery Order or the reception and registration of a Physical Inventory. The module is split into 2 parts:

### Polling

The lx.manager object defines a function called "poll" that is called at intervals by a cron job. It establishes a connection to the FTP server, gets a list of all the present files, and then uses the lx_file object to determine if they need to be processed, and if so, in what order.

Next, an lx.sync record is created to register the date and time of this synchronisation. Then each file to be processed is downloaded, and it's contents is saved into a new lx.file.incoming record and linked to the lx.sync record. Once all files have been downloaded and an lx.file.incoming record created for each one, the cursor is committed. 

### Importing

The next action the poll function takes (continuing from where I left off at the end of the abvoe polling section) is parsing each file. An attempt is made to parse each unparsed lx.file.incoming record, with any failures being written in that records "result" field. 

Next each parsed lx.file.incoming file needs to be converted into one or many lx.updates. Since a single XML file on the FTP server can contain multiple updates (i.e. marking many Delivery Orders as delivered), a single lx.file.incoming record can be linked to many lx.update records. The standard XML header is removed and the remaining elements are saved to an lx.update each.

Finally an attempt is made to execute each unexecuted update. An lx_data subclass is chosen by matching the object_type field of the lx.update record with the object_type field of an lx_data subclass. The found lx_data subclass is then instantiated with the XML file contents as the first and only parameter. The process method is then called on it.

# Extending the Functionality

The complexity of the inner workings of this module lead to simplicity in it's extension. Below I will describe how you can upload new file types, or download new data from LX1.

## Uploading Data

### Create the Hook

1. Create a new hook file in the hooks directory and create a new class
2. Make the class a subclass of the oe_lx class and _inherit an Odoo object
3. Override some method that should be the trigger of the upload, for example create
4. Call self.upload, where the third argument is the browse record to be uploaded, and the second is an lx_data subclass we are about to create

### Define the Serialization

5. Create a new file in the serialization folder with a new class 
6. Make that class a subclass of lx_data
7. Define the object_type and message_identifier fields
8. Override the extract method with one parameter which will contain the browse record(s) defined in the hook class.
9. Extract data from the browse record(s) into an OrderedDict and save it to self.data

### Profit

That is all that is required. Now when the hook is triggered by Odoo, the browse record will be extracted into an lx.file.outgoing record and that will be uploaded to the FTP server.


## Downloading Data

### Defining the importation

1. Create a new file in the serialization folder and write a new class inside it
2. Have the class inherit from lx_data
3. Define an object_type to be the same as the MessageIdentifier in the standard XML header of the file you will receive from LX1
4. Override the process method taking a pool, cr and the dict containing deserialized XML file contents as it's 3 parameters
5. Use the data in the dict to update your Odoo instance

### Profit

That is all that is needed to import new data from LX1. The process of downloading the XML files and matching them to the correct lx_data class and calling process is all done behind the scenes.