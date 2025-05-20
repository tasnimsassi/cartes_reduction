from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class LoyaltyCartController(http.Controller):
    @http.route('/shop/apply_loyalty', type='json', auth='public', website=True)
    def apply_loyalty(self, line_id):
        line = request.env['sale.order.line'].browse(int(line_id))
        if line.exists():
            loyalty_info = line._get_loyalty_info()
            if loyalty_info['best_reward']:
                # Mise à jour directe de la ligne existante
                line.write({
                    'discount': loyalty_info['max_discount'],
                    'price_unit': line.product_id.list_price,
                    'loyalty_reward_id': loyalty_info['best_reward'].id,
                    # Tu peux ajouter d'autres champs ici si tu veux afficher plus d'infos
                })

                return {
                    'success': True,
                    'discount': loyalty_info['max_discount'],
                    'program_name': loyalty_info['best_program'].name,
                    'reward_description': loyalty_info['reward_description'],
                    'card_name': loyalty_info['card_name'],

                }

        return {'success': False}

    @http.route('/shop/cart/update_discounts', type='json', auth="public", website=True)
    def update_discounts(self, force_discount=None, rule_id=None, **kw):
        try:
            try:
                # Début de la section verrouillée
                db_lock = request.env.cr.savepoint()
                order = request.website.sale_get_order(force_create=True)
                if not order:
                    return {'success': False, 'error': 'Order not found'}

                # Conversion des paramètres
                force_discount = float(force_discount) if force_discount else 0
                rule_id = int(rule_id) if rule_id else False

                # Stocker la remise forcée sur la commande
                order.write({
                    'forced_discount': force_discount,
                    'forced_discount_rule_id': rule_id
                })

                # Désactiver les recalculs automatiques
                order = order.with_context(
                    automatic_calculation=False,
                    loyalty_no_messages=True
                )

                # Réinitialisation des remises
                order.order_line.filtered(lambda l: not l.is_reward_line).write({
                    'discount': 0,
                    'loyalty_reward_id': False
                })

                # Appliquer la remise forcée si spécifiée
                if force_discount and rule_id:
                    rule = request.env['product.association'].browse(rule_id)
                    if rule.exists() and rule.card_id:
                        reward = rule.card_id.loyalty_program_id.reward_ids[:1]
                        lines = order.order_line.filtered(lambda l: not l.is_reward_line)
                        lines.write({
                            'discount': force_discount,
                            'loyalty_reward_id': reward.id
                        })

                # Forcer le recalcul
                order._compute_amounts()

                # Préparer la réponse
                result = {
                    'success': True,
                    'amounts': {
                        'amount_total': order.amount_total,
                        'amount_untaxed': order.amount_untaxed,
                        'discounts': {l.id: force_discount if force_discount else l.discount
                                      for l in order.order_line},
                        'forced_discount': force_discount
                    }
                }

                request.env.cr.commit()
                return result

            except Exception as lock_error:
                request.env.cr.rollback()
                _logger.error("Database error: %s", str(lock_error))
                return {'success': False, 'error': 'System busy, please retry'}

        except Exception as e:
            _logger.error("System error: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/shop/cart/update_amounts', type='json', auth="public", website=True)
    def update_amounts(self):
        order = request.website.sale_get_order()
        if not order:
            return {'success': False}

        forced_discount = order.forced_discount or 0

        amounts = {
            'amount_untaxed': order.amount_untaxed,
            'amount_tax': order.amount_tax,
            'amount_total': order.amount_total,
            'discounts': {},
            'forced_discount': forced_discount
        }

        for line in order.order_line:
            if line.discount > 0:
                amounts['discounts'][line.id] = forced_discount if forced_discount else line.discount

        return amounts


    @http.route('/shop/check_product_suggestions', type='json', auth='public', website=True)
    def check_product_suggestions(self, product_ids, **kw):
        """Version optimisée avec préchargement"""
        try:
            if not product_ids:
                return {'success': False, 'suggestions': []}

            rules = request.env['product.association'].search([
                ('antecedent_product_ids', 'in', product_ids),
                ('associated_product_id', '!=', False)
            ])

            suggestions = []
            for rule in rules:
                antecedent_ids = rule.antecedent_product_ids.ids
                if all(pid in product_ids for pid in antecedent_ids):
                    if rule.associated_product_id.id not in product_ids:
                        suggestions.append({
                            'rule_id': rule.id,
                            'product_id': rule.associated_product_id.id,
                            'product_name': rule.associated_product_id.name,
                            'card_name': rule.card_id.name if rule.card_id else '',
                            'loyalty_program_name': rule.card_id.loyalty_program_id.name if rule.card_id.loyalty_program_id.name else '',
                            'reward_discount': rule.card_id.loyalty_program_id.reward_ids.discount if rule.card_id.loyalty_program_id.reward_ids.discount else None,
                        })

            return {'success': True, 'suggestions': suggestions}

        except Exception as e:
            _logger.error("Error in check_product_suggestions: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/shop/apply_product_suggestion', type='json', auth='public', website=True)
    def apply_product_suggestion(self, rule_id, **kw):
        """Applique uniquement le discount de la suggestion"""
        try:
            rule = request.env['product.association'].browse(int(rule_id))
            if not rule.exists():
                return {'success': False}

            order = request.website.sale_get_order()
            if not order:
                return {'success': False}

            # 1. Ajout du produit
            order._cart_update(
                product_id=rule.associated_product_id.id,
                add_qty=1
            )

            # 2. Retourne le discount à appliquer sans le faire directement
            discount = 0
            if rule.card_id and rule.card_id.loyalty_program_id:
                reward = rule.card_id.loyalty_program_id.reward_ids[:1]
                discount = reward.discount if reward else 0

            return {
                'success': True,
                'suggestion_discount': discount,
                'rule_id': rule.id
            }

        except Exception as e:
            _logger.error("Error applying suggestion: %s", str(e))
            return {'success': False, 'error': str(e)}