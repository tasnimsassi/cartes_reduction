from odoo import models, fields

class ProductAssociation(models.Model):
    _name = 'product.association'
    _description = 'Association de produits'

    antecedent_product_ids = fields.Many2many('product.product', string="Produits de base")
    associated_product_id = fields.Many2one('product.product', string="Produit associé", required=True)
    confidence = fields.Float(string='Confiance (%)', required=True)
    support = fields.Float(string='Support (%)', required=True)
    card_id = fields.Many2one('cartes.reduction', string='Carte de réduction associée')
