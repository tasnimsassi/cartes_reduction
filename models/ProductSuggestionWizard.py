from odoo import fields,models


class ProductSuggestionWizard(models.TransientModel):
    _name = 'sale.product.suggestion.wizard'

    order_id = fields.Many2one('sale.order', required=True)
    product_id = fields.Many2one('product.product', required=True)
    card_id = fields.Many2one('cartes.reduction')
    reward_id = fields.Many2one('loyalty.reward')
    coupon_id = fields.Many2one('loyalty.card')
    message = fields.Text()

    def action_add_product(self):
        self.ensure_one()

        # 1. Appliquer d'abord la remise si une carte est associée
        if self.card_id and self.card_id.loyalty_program_id:
            program = self.card_id.loyalty_program_id
            reward = program.reward_ids[0] if program.reward_ids else False

            if reward and reward.reward_type == 'discount':
                # Créer un coupon temporaire
                coupon = self.env['loyalty.card'].sudo().create({
                    'partner_id': self.order_id.partner_id.id,
                    'program_id': program.id,
                    'points': 1,
                })

                # Cette méthode crée automatiquement la ligne de remise
                self.order_id._apply_program_reward(reward, coupon=coupon)

        # 2. Ajouter le produit suggéré (après la remise pour éviter les conflits de calcul)
        line_vals = {
            'order_id': self.order_id.id,
            'product_id': self.product_id.id,
            'name': self.product_id.get_product_multiline_description_sale(),
            'product_uom_qty': 1,
            'product_uom': self.product_id.uom_id.id,
            'price_unit': self.product_id.list_price,
        }
        self.env['sale.order.line'].create(line_vals)



        return {
            'type': 'ir.actions.act_window_close',
            'effect': {
                'fadeout': 'slow',
                'message': 'Produit et remise appliqués avec succès',
                'type': 'rainbow_man'
            }
        }

    def action_skip(self):
        """Ignorer la suggestion"""
        return {'type': 'ir.actions.act_window_close'}