from odoo import models , api, fields
import logging

_logger = logging.getLogger(__name__)
class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.extend(['cartes.attribution', 'cartes.reduction', 'loyalty.program', 'loyalty.reward','product.pricelist','res.partner','product.association'])
        return result

    def _loader_params_cartes_attribution(self):
        return {
            'search_params': {
                'domain': [('state', 'in', ['validated', 'renouvelé'])],
                 'fields': ['client_id', 'carte_ids','loyalty_program_id','date_attribution' , 'date_expiration','state'],
            },
        }

    def _get_pos_ui_cartes_attribution(self, params):
        return self.env['cartes.attribution'].search_read(**params['search_params'])

    def _loader_params_cartes_reduction(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['name', 'state', 'loyalty_program_id',],
            },

        }

    def _get_pos_ui_cartes_reduction(self, params):
        return self.env['cartes.reduction'].search_read(**params['search_params'])

    def _loader_params_loyalty_program(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['name',
                'program_type',
                'reward_ids',
                'pricelist_ids',
                'date_from',
                'date_to',
                'limit_usage',
                'max_usage',

                ]
            },
        }

    def _get_pos_ui_loyalty_program(self, params):
        return self.env['loyalty.program'].search_read(**params['search_params'])

    def _loader_params_product_association(self):
        return {
            'search_params': {
                'domain': [],
                'fields': [
                    'antecedent_product_ids', 'associated_product_id',
                    'confidence', 'support', 'card_id'
                ],
            },
        }

    def _get_pos_ui_product_association(self, params):
        return self.env['product.association'].search_read(**params['search_params'])
class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _process_order(self, order, draft, existing_order):

        # Appel à la méthode parente d'abord
        res = super()._process_order(order, draft, existing_order)

        # Récupération de l'ID du partenaire depuis les données de la commande
        partner_id = order.get('partner_id', False)
        if not partner_id:
            return res

        try:
            partner = self.env['res.partner'].browse(partner_id)

            # Mise à jour des stats client
            partner._compute_purchase_stats()
            partner._compute_customer_segment()

            # Prédictions ML
            partner.update_behavior_analysis()
            partner._predict_ml_metrics()

            # Application des règles
            self.env['promotion.rule'].apply_rules(partner)

        except Exception as e:
            _logger.error(f"Error processing POS order for partner {partner_id}: {str(e)}")

        return res

    def _get_order_categories(self, order_data):
        """Helper pour récupérer les catégories de produits de la commande"""
        product_ids = [line[2]['product_id'] for line in order_data.get('lines', []) if len(line) > 2]
        products = self.env['product.product'].browse(product_ids)
        return products.mapped('categ_id').ids

class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    custom_discount_card_id = fields.Many2one('cartes.reduction', string="Carte de réduction")
    custom_discount_program_id = fields.Many2one('loyalty.program', string="Programme utilisé")

    def _export_for_ui(self, orderline):
        res = super()._export_for_ui(orderline)
        # Ajout des infos de carte de réduction
        res.update({
            'custom_discount_card_id': orderline.custom_discount_card_id.id,
            'custom_discount_program_id': orderline.custom_discount_program_id.id,
            'custom_discount_text': self._get_custom_discount_text(orderline)
        })
        return res

    def _get_custom_discount_text(self, orderline):
        if orderline.custom_discount_card_id and orderline.custom_discount_program_id:
            return f"Remise {orderline.custom_discount_card_id.name}: -{orderline.discount}%"
        return ""
