from openerp.osv import osv

class res_partner(osv.osv):
    """ 
    fields_view_get_address is used to hide the state field depending on chosen country
    but it breaks other functionality like adding required="1" to city and zip fields.
    
    Could not find a better solution to keep the existing behaviour but also add required="1"
    so just disable the functionality for now ...  
    """
    _inherit ="res.partner"
    
    def fields_view_get_address(self, cr, uid, arch, context={}):
        return arch
