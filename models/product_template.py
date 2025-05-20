from odoo import api, models, fields
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_loyalty = fields.Boolean(string="Produit de fidélité")
    client_specific_discount = fields.Float(
        string="Réduction client",
        compute='_compute_client_specific_discount',
    )

    @api.depends_context('uid')  # Assurez-vous que ce décorateur est bien à l'intérieur de la classe
    def _compute_client_specific_discount(self):
        for record in self:
            discount = 0.0
            user = self.env.user
            client = user.partner_id
            carte = client.carte_ids[:1]  # Vous pouvez vérifier la logique ici
            program = carte.loyalty_program_id if carte else None

            _logger.info(f"Client: {client.name}, Carte: {carte}, Programme: {program}")

            if program:
                for rule in program.loyalty_rule_ids:
                    _logger.info(f"Rule: {rule.name}, Product: {rule.product_id}, Discount: {rule.discount}")
                    if rule.product_id and rule.product_id.id == record.id:
                        discount = rule.discount
                        break
                    elif not rule.product_id:
                        discount = rule.discount
            record.client_specific_discount = discount
