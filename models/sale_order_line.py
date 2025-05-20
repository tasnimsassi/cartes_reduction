# cartes_reduction/models/sale_order_line.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    association_rule_id = fields.Many2one('product.association', string='Règle d’Association', readonly=True)
    forced_discount = fields.Float(string="Remise forcée")
    forced_discount_rule_id = fields.Many2one('product.association', string="Règle de remise forcée")
    loyalty_reward_id = fields.Many2one('loyalty.reward', readonly=True)
    @api.constrains('discount')
    def _check_discount_source(self):
        """Empêche l'application de discounts globaux automatiques"""
        for line in self:
            if line.discount > 0 and line.reward_id and line.reward_id.is_global_discount:
                raise ValidationError(_("Les discounts globaux ne sont pas autorisés - utilisez les programmes de fidélité personnalisés"))

    def _get_loyalty_info(self):
        self.ensure_one()
        product = self.product_id
        result = {
            'card_name': False,
            'best_program': False,
            'best_reward': False,
            'max_discount': 0,
            'reward_description': False
        }

        # 1. Vérifier d'abord si une remise forcée (suggestion) est active sur l'ordre
        if self.order_id.forced_discount and self.order_id.forced_discount_rule_id:
            rule = self.order_id.forced_discount_rule_id
            if rule.card_id and rule.card_id.loyalty_program_id:
                reward = rule.card_id.loyalty_program_id.reward_ids[:1]
                return {
                    'card_name': rule.card_id.name,
                    'best_program': rule.card_id.loyalty_program_id,
                    'best_reward': reward,
                    'max_discount': self.order_id.forced_discount,
                    'reward_description': "Remise suggérée"
                }
        best_program = self.order_id.best_loyalty_program_id
        best_card_name = self.order_id.best_loyalty_card_name

        if not best_program:
            return result

        # Vérifier s’il y a une récompense globale 'order'
        order_reward = best_program.reward_ids.filtered(lambda r: r.reward_type == 'order')
        if order_reward:
            result.update({
                'card_name': best_card_name,
                'best_program': best_program,
                'best_reward': order_reward[0],
                'max_discount': order_reward[0].discount,
                'reward_description': order_reward[0].description
            })
            return result

        # Sinon, vérifier les récompenses par produit
        for reward in best_program.reward_ids.filtered(lambda r: r.reward_type in ('discount', 'product')):
            is_applicable = (
                    (reward.reward_product_ids and product in reward.reward_product_ids) or
                    (reward.reward_product_domain and eval(reward.reward_product_domain) + [('id', '=', product.id)] and
                     self.env['product.product'].search_count(
                         eval(reward.reward_product_domain) + [('id', '=', product.id)])) or
                    (not reward.reward_product_ids and not reward.reward_product_domain)
            )
            if is_applicable and reward.discount > result['max_discount']:
                result.update({
                    'card_name': best_card_name,
                    'best_program': best_program,
                    'best_reward': reward,
                    'max_discount': reward.discount,
                    'reward_description': reward.description
                })

        return result

    def _compute_price(self):
        for line in self:
            # Ne PAS interférer si une remise globale est active
            if any(
                    line.loyalty_reward_id and
                    line.loyalty_reward_id.reward_type == 'order'
                    for line in self.order_id.order_line
            ):
                continue

            # Logique normale pour les remises spécifiques
            if line.reward_id and line.reward_id.is_global_discount:
                line.update({
                    'discount': 0,
                    'price_unit': line.product_id.list_price
                })
            else:
                loyalty_info = line._get_loyalty_info()
                if loyalty_info.get('max_discount', 0) > 0:
                    line.update({
                        'discount': loyalty_info['max_discount'],
                        'price_unit': line.product_id.list_price
                    })
                else:
                    super(SaleOrderLine, line)._compute_price()
#mtee3 site web toufa hne
    is_loyalty_line = fields.Boolean(
        string="Ligne de fidélité",
        compute="_compute_is_loyalty_line",
        store=True,
        help="Indique si cette ligne est générée par un programme de fidélité (récompense ou réduction)."
    )

    @api.depends('reward_id')
    def _compute_is_loyalty_line(self):
        for line in self:
            line.is_loyalty_line = bool(line.reward_id)
