from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class PromotionRule(models.Model):
    _name = 'promotion.rule'
    _description = 'Règles de Marketing Automatisé'
    _order = 'sequence,id'

    # ================
    #  CHAMPS DE BASE
    # ================
    name = fields.Char(string="Nom", required=True)
    sequence = fields.Integer(string="Priorité", default=10)
    active = fields.Boolean(string="Active", default=True)

    # ===================
    #  CHAMPS CONDITIONS
    # ===================
    segment_cible = fields.Selection(
        selection=[
            ('new', 'Nouveau Client'),
            ('regular', 'Client Régulier'),
            ('vip', 'Client VIP'),
            ('churned', 'Client Inactif')
        ],
        string="Segment Cible"
    )

    min_rfm_score = fields.Integer(
        string="Score RFM Minimum",
        help="Score minimum RFM (100-500) pour éligibilité"
    )

    condition_min_achats = fields.Float(
        string="Montant Minimum",
        help="Montant total des achats requis"
    )

    condition_frequence = fields.Integer(
        string="Fréquence Max (jours)",
        help="Intervalle maximum entre les commandes"
    )

    product_category_ids = fields.Many2many(
        'product.category',
        string="Catégories Applicables",
        help="Limiter aux produits de ces catégories"
    )

    # ===================
    #  CHAMPS RÉCOMPENSES
    # ===================
    reward_type = fields.Selection(
        selection=[
            ('discount', 'Remise'),
            ('gift_card', 'Carte Cadeau'),
            ('loyalty_points', 'Points'),
            ('free_product', 'Produit Gratuit')
        ],
        string="Type de Récompense",
        required=True
    )

    discount_percent = fields.Float(
        string="% Remise",
        digits=(16, 2)
    )

    discount_product_id = fields.Many2one(
        'product.product',
        string="Produit Remisé"
    )

    gift_card_template_id = fields.Many2one(
        'loyalty.program',
        string="Modèle Carte",
        domain=[('program_type', '=', 'gift_card')]
    )

    loyalty_points = fields.Integer(
        string="Points à Attribuer"
    )

    free_product_id = fields.Many2one(
        'product.product',
        string="Produit Gratuit"
    )

    # =================
    #  MÉTHODES DE BASE
    # =================
    @api.constrains('reward_type', 'discount_percent')
    def _check_discount(self):
        """Validation des remises"""
        for rule in self:
            if rule.reward_type == 'discount' and not rule.discount_percent:
                raise ValidationError("Un pourcentage de remise est requis pour ce type de récompense")

    # ======================
    #  MÉTHODES PRINCIPALES
    # ======================
    def apply_rules(self, partners):
        """Applique les règles aux partenaires éligibles"""
        for rule in self.filtered(lambda r: r.active):
            try:
                eligible_partners = partners.filtered(
                    lambda p: rule._check_conditions(p)
                )
                for partner in eligible_partners:
                    rule._apply_reward(partner)
            except Exception as e:
                _logger.error(f"Erreur application règle {rule.id}: {str(e)}")
                continue

    def _check_conditions(self, partner):
        """Vérifie si le partenaire remplit toutes les conditions"""
        self.ensure_one()
        conditions = []

        # Vérification segment
        if self.segment_cible:
            conditions.append(partner.customer_segment == self.segment_cible)

        # Vérification score RFM
        if self.min_rfm_score:
            conditions.append(partner.rfm_score >= self.min_rfm_score)

        # Vérification montant minimum
        if self.condition_min_achats:
            conditions.append(partner.total_sales >= self.condition_min_achats)

        # Vérification fréquence
        if self.condition_frequence and partner.purchase_frequency:
            conditions.append(partner.purchase_frequency <= self.condition_frequence)

        # Vérification catégories produits (si commande existante)
        if hasattr(self, '_order') and self.product_category_ids:
            order = self._order
            order_categories = order.lines.mapped('product_id.categ_id')
            conditions.append(not self.product_category_ids or order_categories & self.product_category_ids)

        return all(conditions)

    # ======================
    #  MÉTHODES RÉCOMPENSES
    # ======================
    def _apply_reward(self, partner):
        """Applique la récompense appropriée"""
        reward_method = getattr(self, f'_apply_{self.reward_type}', None)
        if reward_method:
            reward_method(partner)
        else:
            _logger.error(f"Méthode de récompense inconnue: {self.reward_type}")

    def _apply_discount(self, partner):
        """Applique une remise"""
        coupon_program = self._get_coupon_program()
        coupon = self.env['loyalty.card'].create({
            'program_id': coupon_program.id,
            'partner_id': partner.id,
            'points': self.discount_percent,
            'expiration_date': fields.Date.today() + timedelta(days=30)
        })
        self._send_notification(
            partner,
            f"Remise de {self.discount_percent}%",
            f"Une remise de {self.discount_percent}% a été appliquée à votre compte!"
        )

    def _apply_gift_card(self, partner):
        """Crée une carte cadeau"""
        if not self.gift_card_template_id:
            raise UserError("Configuration manquante: Modèle de carte cadeau")

        card = self.env['loyalty.card'].create({
            'program_id': self.gift_card_template_id.id,
            'partner_id': partner.id,
            'points': self.gift_card_template_id.point_unit,
            'expiration_date': fields.Date.today() + timedelta(days=365)
        })
        self._send_notification(
            partner,
            f"Carte cadeau {self.gift_card_template_id.name}",
            f"Vous avez reçu une carte cadeau {self.gift_card_template_id.name}!"
        )

    # =====================
    #  MÉTHODES UTILITAIRES
    # =====================
    def _get_coupon_program(self):
        """Trouve le programme de coupons actif"""
        program = self.env['loyalty.program'].search([
            ('program_type', '=', 'coupons'),
            ('active', '=', True)
        ], limit=1)

        if not program:
            raise UserError("Aucun programme de coupons actif n'a été trouvé")
        return program

    def _send_notification(self, partner, subject, body):
        """Envoie une notification au partenaire"""
        self.env['mail.message'].create({
            'model': 'res.partner',
            'res_id': partner.id,
            'body': body,
            'subject': subject,
            'message_type': 'notification',
            'subtype_id': self.env.ref('mail.mt_comment').id
        })