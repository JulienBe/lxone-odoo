import logging
_logger = logging.getLogger(__name__)
from datetime import datetime
from openerp.tools.translate import _

from ads_data import ads_data

class ads_stock(ads_data):
    """
    Receive physical inventories from ADS in a STOC file
    """
    file_name_prefix = ['STOC']
    xml_root = 'stock'

    def pre_process_hook(self, pool, cr):
        """ Create inventory parent object and save ID for later """
        inventory_obj = pool.get('stock.inventory')
        inventory_data = {
            'name': 'Alpha Direct Service Physical Inventory',
            'date': datetime.now()
        }
        self.inventory_id = inventory_obj.create(cr, 1, inventory_data)

    def process(self, pool, cr, physical_inventory):
        """
        Create physical inventory lines and attach them to the parent created
        in the pre-process hook  
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @param physical_inventory: a node of data containing the physical inventory info
        """
        inventory_obj = pool.get('stock.inventory')
        product_obj = pool.get('product.product')

        assert all([field in physical_inventory for field in ['CODE_ART', 'QTE_DISPO']]), \
            _('A physical_inventory has been skipped because it was missing a required field: %s' % physical_inventory)

        # create physical inventory lines and attach them to previously created parent
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
        inventory_obj.write(cr, 1, self.inventory_id, {'inventory_line_id': [(0, 0, line_data)]})

    def post_process_hook(self, pool, cr):
        """ Confirm the inventory after adding all the lines """
        inventory_obj = pool.get('stock.inventory')
        inventory_obj.action_confirm(cr, 1, [self.inventory_id])
