from odoo import models, fields

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    some_field = fields.Char(string="Some Field")
    carte_reduction_id = fields.Many2one('cartes.reduction', string="Carte de Réduction")
    special_discount = fields.Float(string="Remise Spéciale (%)")
    validity_period = fields.Date(string="Période de Validité")