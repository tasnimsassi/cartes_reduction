from odoo import models, api , fields
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    forced_discount = fields.Float(string="Remise forcée")
    forced_discount_rule_id = fields.Many2one('product.association', string="Règle de remise forcée")
    order_line = fields.One2many('sale.order.line', 'order_id', string='Order Lines', copy=True)
    def _create_loyalty_reward_line(self, reward, line=None):
        """Crée une ligne de récompense"""
        vals = {
            'product_id': reward.program_id.reward_product_id.id,
            'name': reward.description,
            'product_uom_qty': 1,
            'price_unit': 0,
            'is_reward_line': True,
            'loyalty_reward_id': reward.id,
            'order_id': self.id
        }
        if line:
            vals['linked_line_id'] = line.id
        return self.env['sale.order.line'].create(vals)

    best_loyalty_program_id = fields.Many2one('loyalty.program', compute='_compute_best_loyalty_program', store=True)
    best_loyalty_card_name = fields.Char(compute='_compute_best_loyalty_program', store=True)

    @api.depends('order_line.product_id', 'partner_id', 'order_line.product_uom_qty')
    def _compute_best_loyalty_program(self):
        for order in self:
            program_info = order._get_best_loyalty_program()
            if program_info:
                order.best_loyalty_program_id = program_info[0].id
                order.best_loyalty_card_name = program_info[1].name
            else:
                order.best_loyalty_program_id = False
                order.best_loyalty_card_name = False

    def _get_best_loyalty_program(self):
        self.ensure_one()
        partner = self.partner_id

        best_program = None
        best_card = None
        max_total_discount = 0

        if not hasattr(partner, 'cartes_attribution_ids'):
            return None

        valid_attributions = partner.cartes_attribution_ids.filtered(
            lambda a: a.state == 'validated' and a.date_expiration >= fields.Date.today()
        )

        for attribution in valid_attributions:
            for card in attribution.carte_ids:
                for program in card.loyalty_program_id:
                    total_discount = 0
                    for line in self.order_line:
                        for reward in program.reward_ids.filtered(lambda r: r.reward_type in ('discount', 'order', 'product')):
                            product = line.product_id
                            is_applicable = False

                            if reward.reward_product_ids and product in reward.reward_product_ids:
                                is_applicable = True
                            elif reward.reward_product_domain and reward.reward_product_domain != '[]':
                                domain = eval(reward.reward_product_domain) + [('id', '=', product.id)]
                                is_applicable = bool(self.env['product.product'].search_count(domain))
                            else:
                                is_applicable = True

                            if is_applicable:
                                total_discount += (reward.discount or 0) * line.product_uom_qty

                    if total_discount > max_total_discount:
                        max_total_discount = total_discount
                        best_program = program
                        best_card = card

        if best_program and best_card:
            return best_program, best_card
        return None

    def _compute_amounts(self):
        """Version optimisée du recalcul"""
        for order in self:
            # Force le recalcul des prix des lignes
            order.order_line._compute_price()

            # Utilise la méthode standard de calcul des totaux
            if hasattr(order, '_amount_all'):
                order._amount_all()
            else:
                # Fallback manuel si _amount_all n'existe pas
                order.amount_untaxed = sum(line.price_subtotal for line in order.order_line)
                order.amount_tax = sum(line.price_tax for line in order.order_line)
                order.amount_total = order.amount_untaxed + order.amount_tax
    def _remove_standard_discounts(self):
        """Supprime toutes les remises standards existantes"""
        self.order_line.filtered(
            lambda l: l.reward_id  # Toutes les lignes de reward standard
        ).unlink()

    def _apply_custom_discounts(self):
        self._remove_standard_discounts()
        return self._apply_best_loyalty()  # Retourne True si remise globale appliquée

    def _get_highest_discount(self):
        """Retourne le pourcentage de la plus haute remise appliquée"""
        return max(
            line.discount
            for line in self.order_line
            if not line.is_reward_line
        )

    def _cart_update(self, product_id, line_id=None, add_qty=0, set_qty=0, **kwargs):
        res = super()._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)
        self._apply_custom_discounts()
        return res

    def update_existing_lines(self):
        """Méthode pour mettre à jour les lignes existantes"""
        self._apply_custom_discounts()
        return True

    def _add_loyalty_reward_line(self, program, reward, order_line=None):
        """Crée une ligne de récompense dans la commande"""
        vals = {
            'product_id': program.reward_product_id.id,
            'name': reward.description,
            'product_uom_qty': 1,
            'price_unit': 0,
            'is_reward_line': True,
            'loyalty_reward_id': reward.id,
            'order_id': self.id
        }

        if order_line:
            vals.update({
                'linked_line_id': order_line.id,
                'sequence': order_line.sequence + 1
            })

        return self.env['sale.order.line'].create(vals)

    #toufaaa hne
    applied_discount_card_id = fields.Many2one(
        'cartes.reduction',
        string="Carte de réduction appliquée",
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    @api.depends('order_line')
    def _compute_discount_display(self):
        for order in self:
            if order.applied_discount_card_id:
                order.discount_display = f"{order.applied_discount_card_id.discount}% ({order.applied_discount_card_id.name})"
            else:
                order.discount_display = False

    discount_display = fields.Char(compute='_compute_discount_display')



    def _get_applied_discount_text(self):
        self.ensure_one()
        if self.applied_discount_card_id:
            return f"{self.applied_discount_card_id.discount}% avec {self.applied_discount_card_id.name}"
        return "Aucune réduction appliquée"

    selected_reward_id = fields.Many2one(
        'loyalty.reward',
        string="Récompense sélectionnée"
    )

    selected_carte_id = fields.Many2one(
        'cartes.reduction',
        string="Carte sélectionnée"
    )
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            print(f"Client changé - ID: {self.partner_id.id}, Nom: {self.partner_id.name}")
            self._get_ui_cartes_data(self.partner_id.id)
        else:
            print("Aucun client sélectionné.")

    def _get_ui_cartes_data(self, partner_id):
        partner = self.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {}

        attributions = self.env['cartes.attribution'].search([
            ('client_id', '=', partner.id),
            ('state', 'in', ['renouvelé', 'validated'])
        ])

        reductions = attributions.mapped('carte_ids')
        programs = reductions.mapped('loyalty_program_id')

        result = {
            'cartes_reduction': [(6, 0, reductions.ids)],
            'loyalty_programs': [(6, 0, programs.ids)],
        }

        print("\n=== Résultat _get_ui_cartes_data ===")
        print(result)
        print("====================================\n")

        return result

    def action_open_reward_wizard(self):
        self.ensure_one()
        if not self.partner_id:
            return {
                'warning': {
                    'title': "Aucun client sélectionné",
                    'message': "Veuillez sélectionner un client avant de continuer."
                }
            }

        data = self._get_ui_cartes_data(self.partner_id.id)

        if not data.get('cartes_reduction')[0][2] and not data.get('loyalty_programs')[0][2]:
            return {
                'warning': {
                    'title': "Pas de programmes",
                    'message': "Aucun programme de fidélité ou carte disponible pour ce client."
                }
            }

        return {
            'name': "Choisir un Programme de Fidélité",
            'type': 'ir.actions.act_window',
            'res_model': 'reward.selection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_cartes_info': data['cartes_reduction'],
                'default_loyalty_programs_info': data['loyalty_programs'],
            }
        }

    @api.depends('order_line', 'applied_coupon_ids')
    def _compute_promo(self):
        self._update_programs_and_rewards()

    def _cart_update(self, product_id, line_id=None, add_qty=0, set_qty=0, **kwargs):
        res = super()._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)

        # Réappliquer vos discounts après chaque mise à jour
        if self.website_id:
            for line in self.website_order_line:
                if hasattr(line, '_get_loyalty_info'):
                    loyalty_info = line._get_loyalty_info()
                    if loyalty_info.get('max_discount', 0) > 0:
                        line.write({
                            'discount': loyalty_info['max_discount'],
                            'price_unit': line.product_id.list_price
                        })

        return res

    def _check_product_suggestions(self):
        self.ensure_one()
        if not self.partner_id:
            return False

        rules = self.env['product.association'].search([])
        ordered_product_ids = self.order_line.mapped('product_id').ids

        for rule in rules:
            if all(pid in ordered_product_ids for pid in rule.antecedent_product_ids.ids):
                if rule.associated_product_id.id not in ordered_product_ids:
                    reward = None
                    if rule.card_id and rule.card_id.loyalty_program_id:
                        program = rule.card_id.loyalty_program_id
                        reward = program.reward_ids[0] if program.reward_ids else None

                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Suggestion de Produit',
                        'res_model': 'sale.product.suggestion.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_order_id': self.id,
                            'default_product_id': rule.associated_product_id.id,
                            'default_card_id': rule.card_id.id if rule.card_id else None,
                            'default_reward_id': reward.id if reward else None,
                            'default_message': f"Ajoutez {rule.associated_product_id.name} pour bénéficier de la remise {rule.card_id.name if rule.card_id else ''}",
                        }
                    }
        return False

    def action_confirm(self):
        """Override pour vérifier les suggestions avant confirmation"""
        suggestion = self._check_product_suggestions()
        if suggestion:
            return suggestion
        return super().action_confirm()

    def _apply_best_loyalty(self):
        """Applique la meilleure remise de fidélité disponible"""
        self.ensure_one()
        for line in self.order_line:
            if not line.is_reward_line:
                loyalty_info = line._get_loyalty_info()
                if loyalty_info['best_reward']:
                    line.write({
                        'discount': loyalty_info['max_discount'],
                        'loyalty_reward_id': loyalty_info['best_reward'].id,
                    })