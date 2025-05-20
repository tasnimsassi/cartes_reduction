from odoo import models, fields, api
from odoo.exceptions import ValidationError
class CartePromotion(models.Model):
    _name = 'cartes.promotions'
    _description = "Promotions des Cartes de Réduction"

    name = fields.Char(string="Nom de la Promotion", required=True)
    discount = fields.Float(string="Réduction (%)")
    carte_id = fields.Many2one('cartes.reduction', string="Carte Associée")

    @api.constrains('discount')
    def _check_discount(self):
        for record in self:
            if record.discount < 0:
                raise ValidationError("La réduction ne peut pas être négative.")

