import logging
_logger = logging.getLogger(__name__)
from datetime import datetime
from openerp.tools.translate import _

from auto_vivification import AutoVivification
from ads_data import ads_data

class ads_stock(ads_data):

    file_name_prefix = ['STOC']
    xml_root = 'stock'

    def process(self, pool, cr):
        """
        Receive physical inventories from ADS in a STOC file
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @returns True if successful. If True, the xml file on the FTP server will be deleted.
        """

        root_key = self.data.keys()[0]

        if isinstance(self.data[root_key], AutoVivification):
            self.data[root_key] = [self.data[root_key]]

        inventory_obj = pool.get('stock.inventory')
        product_obj = pool.get('product.product')

        # setup physical inventory parent object
        inventory_data = {
            'name': 'Alpha Direct Service Physical Inventory',
            'date': datetime.now()
        }
        inventory_id = inventory_obj.create(cr, 1, inventory_data)

        # create physical inventory lines
        for physical_inventory in self.data[root_key]:
            
            if not all([field in physical_inventory for field in ['CODE_ART', 'QTE_DISPO']]):
                _logger.warn(_('A physical_inventory has been skipped because it was missing a required field: %s' % physical_inventory))
                continue

            product_code = physical_inventory['CODE_ART']
            product_quantity = physical_inventory['QTE_DISPO']
            product_id = product_obj.search(cr, 1, [('x_new_ref', '=', product_code)])
            assert product_id, _("Could not find product with code '%s'" % product_code)
            product = product_obj.browse(cr, 1, product_id[0])

            line_data = {
                'product_id': product.id,
                'product_uom': product.product_tmpl_id.uom_id.id,
                'product_qty': product_quantity,
            }
            inventory_obj.write(cr, 1, inventory_id, {'inventory_line_id': [(0, 0, line_data)]})
            
        # confirm physical inventory
        inventory_obj.action_confirm(cr, 1, [inventory_id])

        return True
