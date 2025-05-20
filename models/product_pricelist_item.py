from odoo import models, fields

class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    some_field = fields.Char(string="Some Field")
