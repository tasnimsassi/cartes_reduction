from datetime import date, timedelta

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class AttributionCarte(models.Model):
    _name = 'cartes.attribution'
    _description = "Attribution de Carte à un Client"

    # Relation avec le modèle res.partner
    client_id = fields.Many2one('res.partner', string="Client", required=True)
    loyalty_program_id = fields.Many2many('loyalty.program', string="Programme de Fidélité")
    # Champ related pour faciliter les calculs
    max_discount = fields.Float(related='loyalty_program_id.reward_ids.discount',
                                string="Remise maximale",
                                store=True)
    # Champs relatifs au client (issus de res.partner)
    client_name = fields.Char(related="client_id.name", string="Nom", readonly=True)
    client_num_telephone = fields.Char(related="client_id.phone", string="Numéro de Téléphone", readonly=True)
    client_email = fields.Char(related="client_id.email", string="Email", readonly=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validé'),
        ('expired', 'Expiré'),
        ('renouvelé', 'Renouvelé'),
    ], string="Statut", default="draft")
    def action_cartes_attribution_list(self):
        """ Action pour afficher la liste des clients avec leurs cartes """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Liste des Clients avec Cartes',
            'view_mode': 'tree,form',
            'res_model': 'cartes.attribution',
            'target': 'current',
        }
    # Champs relatifs à l'attribution de carte
    carte_ids = fields.Many2many('cartes.reduction', string="Cartes de Réduction", required=True)
    date_attribution = fields.Date(string="Date d'Attribution", default=fields.Date.context_today)
    date_expiration = fields.Date(string="Date d'Expiration", required=True)

    def renouveler_carte(self):
        """Renouvelle les cartes attribuées à un client"""
        for record in self:
            if not record.carte_ids:
                raise ValidationError("Aucune carte attribuée à renouveler !")

            cartes_expirees = record.carte_ids.filtered(lambda c: c.date_expiration < fields.Date.today())

            if not cartes_expirees:
                raise ValidationError("Toutes les cartes sont encore valides !")

            for carte in cartes_expirees:
                nouvelle_date_expiration = fields.Date.today() + timedelta(days=365)
                carte.write({
                    'date_debut': fields.Date.today(),
                    'date_expiration': nouvelle_date_expiration,
                    'state': 'active'
                })

            record.write({'date_expiration': max(record.carte_ids.mapped('date_expiration'))})
    @api.onchange('carte_ids')
    def _check_nombre_utilisateurs(self):
        """ Vérifie si le nombre d'utilisateurs n'a pas dépassé la limite. """
        for carte in self.carte_ids:
            if carte.nombre_utilisateurs >= carte.nombre_utilisateurs_max:
                raise UserError("Le nombre d'utilisateurs autorisés pour cette carte a été atteint.")
            else:
                carte.nombre_utilisateurs += 1

    @api.onchange('date_attribution', 'date_expiration')
    def _check_dates(self):
        """ Vérifie si la date d'expiration est postérieure à la date d'attribution. """
        if self.date_expiration and self.date_attribution and self.date_expiration < self.date_attribution:
            raise UserError("La date d'expiration ne peut pas être antérieure à la date d'attribution.")

    def action_attribuer(self):
        """ Méthode pour effectuer l'attribution de carte. """
        for record in self:
            record.write({'state': 'attribué'})  # Exemple d'une mise à jour d'état



    @api.depends('client_id', 'carte_ids')
    def _compute_display_name(self):
        for record in self:
            carte_names = ", ".join(record.carte_ids.mapped('name'))
            record.display_name = f"{record.client_id.name} - {carte_names}"

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.model
    def action_renouveler(self):
        for record in self:
            # Mettez à jour la date d'expiration
            record.date_expiration = fields.Date.today() + timedelta(days=365)  # Par exemple, ajouter 1 an
            record.state = 'active'  # Changez l'état de la carte à active

    @api.depends('date_expiration')
    def _compute_message(self):
        for record in self:
            if record.date_expiration and record.date_expiration < fields.Date.today():
                record.message = "Aucune carte expirée pour le moment"
            else:
                record.message = False

    message = fields.Char(compute='_compute_message', store=False)

    def action_ouvrir_wizard_renouvellement(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Renouveler Carte',
            'res_model': 'wizard.renouvellement.carte',
            'view_mode': 'form',
            'view_id': self.env.ref('cartes_reduction.view_wizard_renouvellement_form').id,
            'target': 'new',
            'context': {'default_attribution_id': self.id},
        }

    def _cron_check_expired_cards(self):
        """Méthode appelée par le cron pour vérifier les cartes expirées"""
        expired_cards = self.search([
            ('date_expiration', '<', fields.Date.today()),
            ('state', '=', 'validated')
        ])
        expired_cards._notify_expired_cards()

    def _notify_expired_cards(self):
        """Notifie les clients dont les cartes sont expirées"""
        Mail = self.env['mail.mail']
        Notification = self.env['notifications.client']

        for card in self:
            # Envoyer l'email
            mail_values = {
                'subject': f"Votre carte {card.carte_ids.name} est expirée",
                'body_html': f"""
                    <div>
                        <p>Bonjour {card.client_id.name},</p>
                        <p>Votre carte {card.carte_ids.name} est expirée depuis le {card.date_expiration}.</p>
                        <p>Pour renouveler, contactez notre service client.</p>
                        <p>Cordialement,<br/>L'équipe {self.env.company.name}</p>
                    </div>
                """,
                'email_to': card.client_id.email,
                'email_from': self.env.user.email,
            }
            mail = Mail.create(mail_values)
            mail.send()

            # Créer la notification
            Notification.create({
                'name': f"Carte {card.carte_ids.name} expirée",
                'message': f"Notification envoyée à {card.client_id.email}",
                'client_id': card.client_id.id,
                'date': fields.Datetime.now(),
            })

            # Mettre à jour le statut
            card.write({'state': 'expired'})

    #hedhi mtee3 gift card
