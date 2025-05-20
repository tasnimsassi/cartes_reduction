

from odoo import fields, models


class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'
    # Définition du champ 'new_field'
    new_field = fields.Char(string='New Field')
    # Champ One2many pour lier les cartes de réduction à ce programme de fidélité
