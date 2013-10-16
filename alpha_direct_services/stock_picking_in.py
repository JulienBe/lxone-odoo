#!/usr/bin/python

from copy import copy
from openerp.osv import osv, fields
from ads_purchase_order import ads_purchase_order

class stock_picking_in(osv.osv):
	"""
	Inherit the stock.picking.in object to trigger 
	document uploading at the appropriate state
	and add ads_sent flag
	"""
	_inherit = 'stock.picking.in'
	_columns = {
		'ads_sent': fields.boolean('Sent to ADS?', help="This field indicates whether or not this document has been uploaded to Alpha Direct Systems for processing."),
		'ads_result': fields.text('ADS Send Results', help="If there are any errors while sending this document to ADS, they will be logged here"),
	}

	def write(self, cr, uid, ids, values, context=None):
		"""
		On write, if state is changed to 'assigned', create a document
		containing the data for the IN and upload it to the ADS server.
		If the upload is successful, set ads_sent to true. Otherwise
		set it to false and save the exception message in ads_result.
		"""
		if True == True: #'state' in values and values['state'] == 'assigned':
			for i in ids:
				vals = copy(values)
				picking = self.browse(cr, uid, i, context=context)
				data = ads_purchase_order()
				data.extract_picking_in(picking)
				try:
					self.pool.get('ads.connection').connect(cr).upload_data(data)
					vals['ads_sent'] = True
				except Exception, e:
					vals['ads_sent'] = False
					vals['ads_result'] = str(e)
				super(stock_picking_in, self).write(cr, uid, i, vals, context=context)
			return True
		else:
			super(stock_picking_in, self).write(cr, uid, i, values, context=context)
