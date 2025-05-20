from odoo import models


class Website(models.Model):
    _inherit = 'website'

    def get_partner_discount_cards(self):
        """Charge les cartes de réduction du partenaire connecté"""
        partner = self.env.user.partner_id
        if not partner:
            return []

        return self.env['cartes.attribution'].search([
            ('client_id', '=', partner.id),
            ('state', '=', 'validated')
        ]).mapped('carte_ids')

    def _loader_params_product_association(self):
        params = {
            'search_params': {
                'domain': [],
                'fields': [
                    'id', 'antecedent_product_ids',
                    'associated_product_id', 'card_id',
                    'associated_product_id.name',
                    'card_id',
                    'card_id.loyalty_program_id',  # Programme lié
                    'card_id.loyalty_program_id.name',  # Nom du programme
                    'card_id.loyalty_program_id.program_type',  # Type de programme
                    'card_id.loyalty_program_id.reward_ids',  # Récompenses du programme
                    'card_id.loyalty_program_id.reward_ids.discount',  # Remise
                    'card_id.loyalty_program_id.reward_ids.reward_type',  # Type de récompense
                    'card_id.loyalty_program_id.reward_ids.name'  # Nom de la récompense
                            ]
            },
        }
        print("Params for product association: %s", params)
        return params

    def _get_ui_product_association(self, params):
        result = self.env['product.association'].search_read(**params['search_params'])
        print("Loaded %d association rules", len(result))
        return result