from odoo import api, models,fields
from odoo.exceptions import UserError, ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'
    # Ajoutez vos champs personnalisés ici
    my_custom_field = fields.Char(string="Mon champ personnalisé")

    is_e_wallet = fields.Boolean("E-Wallet")
    is_loyalty_reward = fields.Boolean("Loyalty Reward")
