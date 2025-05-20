from odoo import models, fields

class CarteCondition(models.Model):
    _name = 'cartes.conditions'
    _description = "Conditions d'Obtention des Cartes"

    name = fields.Char(string="Nom de la Condition", required=True)
    description = fields.Text(string="Description de la Condition")
    active = fields.Boolean(string="Active", default=True)
