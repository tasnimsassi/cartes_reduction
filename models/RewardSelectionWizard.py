from odoo import models, fields, api
from odoo.exceptions import UserError

class RewardSelectionWizard(models.TransientModel):
    _name = 'reward.selection.wizard'
    _description = "Sélection de Programme de Fidélité et Carte"

    sale_order_id = fields.Many2one('sale.order', string="Devis associé")
    cartes_info = fields.Many2many('cartes.reduction', string="")
    loyalty_programs_info = fields.Many2many('loyalty.program', string="")

    selected_carte_id = fields.Many2one(
        'cartes.reduction',
        string="Carte sélectionnée",
        domain="[('id', 'in', cartes_info)]"
    )
    selected_program_id = fields.Many2one(
        'loyalty.program',
        string="Programme de fidélité",
        domain="[('id', 'in', loyalty_programs_info)]"
    )
    selected_reward_id = fields.Many2one(
        'loyalty.reward',
        string="Récompense",
        domain="[('program_id', '=', selected_program_id)]"
    )

    @api.onchange('selected_program_id')
    def _onchange_selected_program_id(self):
        self.selected_reward_id = False
        if self.selected_program_id:
            rewards = self.env['loyalty.reward'].search([
                ('program_id', '=', self.selected_program_id.id)
            ])
            print("Rewards trouvés : ", rewards.ids)
            return {
                'domain': {
                    'selected_reward_id': [('id', 'in', rewards.ids)]
                }
            }
        return {
            'domain': {
                'selected_reward_id': [('id', 'in', [])]
            }
        }

    def action_validate_selection(self):
        self.ensure_one()
        if not self.selected_reward_id:
            raise UserError("Veuillez sélectionner une récompense")

        # Solution alternative pour les modèles personnalisés
        if self.selected_carte_id:
            # Créez un coupon temporaire compatible
            coupon = self.env['loyalty.card'].create({
                'partner_id': self.sale_order_id.partner_id.id,
                'program_id': self.selected_program_id.id,
                'points': 1,  # Valeur minimale requise
            })
        else:
            coupon = False

        # Applique la récompense
        self.sale_order_id._apply_program_reward(
            self.selected_reward_id,
            coupon=coupon
        )

        return {
            'type': 'ir.actions.act_window_close',
            'effect': {
                'fadeout': 'slow',
                'message': 'Réduction appliquée avec succès',
                'type': 'rainbow_man'
            }
        }