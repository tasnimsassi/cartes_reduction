from datetime import date, timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CarteReductionInfo(models.Model):
    _name = 'cartes.reduction.info'
    _description = "Informations des Cartes de Réduction"

    name = fields.Char()
    description = fields.Text()
    image = fields.Char()