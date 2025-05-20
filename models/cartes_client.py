
from odoo import models, fields, api
class Client(models.Model):
    _name = 'cartes.client'
    _description = "Client"

    name = fields.Char(string="Nom", required=True)
    prenom = fields.Char(string="Prénom", required=True)
    num_telephone = fields.Char(string="Numéro de Téléphone", required=True)
    cin = fields.Char(string="CIN", required=True, unique=True)
    carte_ids = fields.Many2many('cartes.reduction', string="Cartes de Réduction")
