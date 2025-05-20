from odoo import models, fields, api

from odoo import models
class NotificationClient(models.Model):
    _name = 'notifications.client'
    _description = "Notifications des Clients"
    name = fields.Char(string="Titre")
    message = fields.Text(string="Contenu")
    client_id = fields.Many2one('res.partner', string="Client")
    date = fields.Datetime(string="Date", default=fields.Datetime.now)
    notification_type = fields.Selection([
        ('vip', 'VIP'),
        ('expired_card', 'Carte expirée'),
        ('newsletter', 'Newsletter'),
    ], string="Type de notification")
