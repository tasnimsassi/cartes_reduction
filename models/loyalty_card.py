from odoo import fields, models


class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    new_field = fields.Char(string='New Field')