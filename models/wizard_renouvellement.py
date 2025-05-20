from odoo import models, fields, api
from datetime import date

class WizardRenouvellementCarte(models.TransientModel):
    _name = 'wizard.renouvellement.carte'
    _description = "Renouvellement de carte expirée"

    date_expiration = fields.Date(string="Nouvelle Date d'Expiration", required=True, default=date.today())
    attribution_id = fields.Many2one('cartes.attribution', string="Carte à renouveler")
    client_id = fields.Many2one('res.partner', string="Client", readonly=True)
    carte_ids = fields.Many2many('cartes.reduction', string="Cartes de Réduction", required=True)

    def action_renouveler(self):
        """ Met à jour la carte avec la nouvelle date d'expiration """
        if self.attribution_id:
            self.attribution_id.write({'date_expiration': self.date_expiration, 'state': 'renouvelé'})
