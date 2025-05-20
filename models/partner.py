from odoo import models, fields

class Partner(models.Model):
    _inherit = 'res.partner'

    carte_ids = fields.One2many('cartes.attribution', 'client_id', string="Cartes de Réduction")
