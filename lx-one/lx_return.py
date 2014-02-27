# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)
from openerp.tools.translate import _
from openerp.osv import osv

from ads_data import ads_data
from tools import parse_date

class ads_return(ads_data):
    """
    Receive a CRET file from ADS. It will contain a node for each return LINE (unmerged 
    product and quantity returned) with the name of the original picking (regardless of splits).

    Because OpenERP lets you return more than the quantity of products specified on the
    picking, simply loop on all CRET nodes, find the named picking, get all linked
    backorder pickings, then find a picking with a matching product name to return quantity
    specified by ADS.

    We cannot differenciate between pickings because an arbitrary number can be returned
    in an arbitrary number of batches, and ADS does not know about our split picking codes.
    """

    file_name_prefix = ['CRET']
    xml_root = 'Retour'

    return_code_mapping = {
        'NP': 'NPAI / Déménagé',
        'AI': 'Adresse Insuffisante',
        'NR': 'Non Réclamé',
        'KC': 'Endommagé',
        'RF': 'Refusé',
        'RD': 'Retour Demandé',
        'ND': 'B.Postale/Porte Codée',
        'RR': 'Résiliation / Décédé',
        'RC': 'Retour avec courriers',
        'RCLI': 'Retour Direct Client',
    }
    
    resend_codes = ['KC', 'RD', 'RC']

    def process(self, pool, cr, ret):
        """
        Receive return in a CRET file and import into OpenERP
        @param pool: OpenERP object pool
        @param cr: OpenERP database cursor
        @param AutoVivification ret: Contains data from ADS describing the return
        """
        # extract data
        ret = self._extract_data(ret)

        # perform return
        self._process_return(pool, cr, ret)

    def _extract_data(self, ret):
        """
        Extract data from a return node sent by ADS. picking_name and return_code
        are required.
        """
        assert all([field in ret for field in ['NUM_FACTURE_BL', 'CODE_MOTIF_RETOUR']]), \
            _('A return has been skipped because it was missing a required field: %s' % ret)
        
        ret_data = {}
        ret_data['picking_name'] = ret['NUM_FACTURE_BL']
        ret_data['return_code'] = ret['CODE_MOTIF_RETOUR']
        ret_data['return_reason'] = self.safe_get(self.return_code_mapping, ret_data['return_code']) \
                                    or _('Code not recognised: ') + ret_data['return_code']
        ret_data['return_date'] = parse_date(self.safe_get(ret, 'DATE_RETOUR'))
        ret_data['product_code'] = self.safe_get(ret, 'CODE_ART')
        ret_data['quantity_sent'] = self.safe_get(ret, 'QTEEXP')
        ret_data['quantity_returned'] = self.safe_get(ret, 'QTERET')
        return ret_data

    def _find_picking(self, pool, cr, ret):
        """
        Finds an appropriate picking to use to process the return.

        This function finds the picking name specified by ADS, then all of its
        backorders. 

        It then loops over each picking, skipping if state is not either done, confirmed
        or assigned.

        Next it loops over stock moves in the picking and checks the state is done,
        the product code matches the one specified by ADS, and it hasn't been 
        completely returned yet.

        Once all of the above criteria are satisfied, it will return the picking ID.
        If no appropriate picking is found it means either we recieved the wrong picking
        name from ADS, the picking has not yet been marked as delivered, or the lines
        have been completely returned already.

        @param dict ret: A dictionary of return data from ADS. See self._extract_data
        """
        picking_obj = pool.get('stock.picking')
        pickings = []
        
        # get original picking
        picking_domain = [('type', '=', 'out'), '!', ('name', 'ilike', 'ret')]
        picking_ids = picking_obj.search(cr, 1, [('name', '=', ret['picking_name'])])
        assert picking_ids, _("Could not find picking with name '%s'" % ret['picking_name'])
        picking = picking_obj.browse(cr, 1, picking_ids[0])
        pickings.append(picking)
        
        # get any backorder pickings 
        backorder_ids = picking_obj.search(cr, 1, [('backorder_id', '=', ret['picking_name'])] + picking_domain)
        while(backorder_ids):
            picking = picking_obj.browse(cr, 1, backorder_ids)
            pickings += picking
            backorder_ids = picking_obj.search(cr, 1, [('backorder_id', 'in', [p.name for p in picking])] + picking_domain)

        # find picking in appropriate state
        for picking in pickings:
            if not picking.state in ['done','confirmed','assigned']:
                continue
            
            # find move in done state, for specified product code, that has not yet been returned
            return_history = pool.get('stock.return.picking').get_return_history(cr, 1, picking.id)
            for move in picking.move_lines:
                if all([
                       move.state == 'done',
                       move.product_id.x_new_ref == ret['product_code'],
                       move.product_qty * move.product_uom.factor > return_history.get(move.id, 0),
                    ]):
                    return picking.id
        raise ValueError(_("Could not find an appropriate picking to close for product code '%s' and picking name '%s'" % (ret['product_code'], ret['picking_name'])))
    
    def _process_return(self, pool, cr, ret):
            """
            Executes the return wizard for a picking, then mark it as received
            @param pool: OpenERP object pool
            @param cursor cr: OpenERP database cursor
            @param dict ret: Dictionary containing return data. See self._extract_data documentation
            """
            # validate params and find picking
            assert ret['picking_name'], _("A picking was received from ADS without a name, so we can't process it")
            picking_id = self._find_picking(pool, cr, ret)
            assert picking_id, _("Could not find appropriate BL to return for original BL %s" % ret['picking_name'])

            # create a wizard record for this picking. Exception thrown if already returned
            context = {
                'active_model': 'stock.picking.out',
                'active_ids': [picking_id],
                'active_id': picking_id,
            }
            wizard_obj = pool.get('stock.return.picking')
            try:
                wizard_id = wizard_obj.create(cr, 1, {'invoice_state': '2binvoiced'}, context=context)
            except osv.except_osv as e:
                if 'No products to return' in e.value:
                    raise ValueError(_('Delivery Order with name "%s" is already fully returned' % ret['picking_name']))
                else:
                    raise e
            wizard = wizard_obj.browse(cr, 1, wizard_id)

            # Set return lines to returned quantity, or 0
            for wizard_line in wizard.product_return_moves:
                if wizard_line.product_id.x_new_ref == ret['product_code']:
                    pool.get('stock.return.picking.memory').write(cr, 1, wizard_line.id,
                        {'quantity': ret['quantity_returned']})
                else:
                    pool.get('stock.return.picking.memory').write(cr, 1, wizard_line.id, {'quantity': 0})

            return_details = wizard_obj.create_returns(cr, 1, [wizard_id], context=context)
            
            # write return reason to additional info box  
            return_id, = eval(return_details['domain'])[0][2]
            pool.get('stock.picking.in').write(cr, 1, return_id, {'note': ret['return_reason']})
            
            # mark return as received
            context = {
                'active_model': 'stock.picking.in',
                'active_ids': [return_id],
                'active_id': return_id,
            }
            wizard_obj = pool.get('stock.partial.picking')
            wizard_id = wizard_obj.create(cr, 1, {'date': ret['return_date']}, context=context)
            wizard = wizard_obj.browse(cr, 1, wizard_id)

            wizard_obj.do_partial(cr, 1, [wizard_id])
            
            # depending on return reason, return the return (i.e. create delivery order to re-send
            # the returned products to the customer
            if ret['return_code'] in self.resend_codes:
                context = {
                    'active_model': 'stock.picking.in',
                    'active_ids': [return_id],
                    'active_id': return_id,
                }
                wizard_obj = pool.get('stock.return.picking')
                try:
                    wizard_id = wizard_obj.create(cr, 1, {'invoice_state': 'none'}, context=context)
                except osv.except_osv as e:
                    if 'No products to return' in e.value:
                        raise ValueError(_('Could not return the return (Re-send to customer) for return with ID %s' % return_id))
                    else:
                        raise e
                wizard_obj.create_returns(cr, 1, [wizard_id], context=context)
