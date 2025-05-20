from datetime import date, timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CarteReduction(models.Model):
    _name = 'cartes.reduction'
    _description = "Cartes de Réduction des Clients"


    name = fields.Char(string="Nom de la Carte", required=True)  # Nom de la carte
    code = fields.Char(string="Code")
    percent = fields.Float(string="Pourcentage de réduction")
    carte_type = fields.Selection([
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('bronze', 'Bronze')
    ], string="Type de Carte", default='standard', required=True)  # Type de carte
    discount = fields.Float(string="Réduction (%)", default=5.0)  # Remise de bienvenue
    date_debut = fields.Date(string="Date de Début")  # Date de début (non affichée dans l'interface)
    date_expiration = fields.Date(string="Date d'Expiration")  # Date d'expiration (non affichée dans l'interface)
    logo = fields.Binary(string="Logo de la Carte")  # Logo de la carte
    nombre_utilisateurs = fields.Integer(string="Nombre d'Utilisateurs Permis", default=0)  # Nombre de clients
    nombre_utilisateurs_max = fields.Integer(string="Nombre d'Utilisateurs Maximum", default=5)
    conditions_ids = fields.Many2many('cartes.conditions', string="Conditions d'Obtention")  # Conditions d'obtention
    active = fields.Boolean(string="Active", default=True)  # Carte active ou non
    loyalty_program_id = fields.Many2many('loyalty.program', string="programme de fedilité")

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'Active'),
        ('archived', 'Archivée'),
    ], default='draft', string='Statut')
    # ce champ pour filtrer les programmes spécifiques
    is_carte_reduction = fields.Boolean(string="Pour Cartes de Réduction")


    @api.constrains('date_debut', 'date_expiration')
    def _check_dates(self):
        for record in self:
            if record.date_expiration and record.date_debut and record.date_expiration < record.date_debut:
                raise ValidationError("La date d'expiration doit être après la date de début.")

    def renouveler_carte(self):
        """Renouvelle la carte attribuée à un client"""
        for record in self:
            if not record.carte_ids:
                raise ValidationError("Aucune carte attribuée !")

            # Vérification de la date d'expiration
            if record.date_expiration < fields.Date.today():
                nouvelle_date_expiration = fields.Date.today() + timedelta(days=365)
                record.write({
                    'date_attribution': fields.Date.today(),
                    'date_expiration': nouvelle_date_expiration,
                    'state': 'active'
                })
            else:
                raise ValidationError("La carte n'est pas encore expirée !")

    def get_loyalty_card_values(self):
        return {
            'partner_id': self.client_id.id,
            'program_id': self.loyalty_program_id.id,
            'points': 1,  # Valeur par défaut
            'code': self.name,
        }

    @api.depends()
    def _compute_stats(self):
        for card in self:
            stats = self.env['carte.usage.stats'].search([('carte_id', '=', card.id)])
            card.usage_count = sum(stats.mapped('usage_count'))
            card.total_discount = sum(stats.mapped('total_discount'))

    usage_count = fields.Integer(compute='_compute_stats', store=False)
    total_discount = fields.Float(compute='_compute_stats', store=False)

    # hedhi teb3a gift card

