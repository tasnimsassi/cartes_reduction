import os
from odoo.tools import config

from odoo import models, fields, api
import logging
from datetime import datetime, timedelta

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CustomerMLCron(models.Model):
    _name = 'customer.ml.cron'
    _description = 'Mise à jour des prédictions ML'

    # Nouveaux champs pour configurer le cron
    batch_size = fields.Integer(
        string="Taille du lot",
        default=1000,
        help="Nombre maximum de clients à traiter en une exécution"
    )

    last_execution = fields.Datetime(
        string="Dernière exécution",
        readonly=True
    )

    processed_partners = fields.Integer(
        string="Clients traités",
        readonly=True
    )

    def _cron_update_predictions(self):
        """Version optimisée"""
        try:
            # 1. D'abord entraîner le modèle si nécessaire
            trainer = self.env['ml.model.trainer']
            model_path = os.path.join(
                config['data_dir'],
                'ml_models',
                'model.pkl'
            )

            if not os.path.exists(model_path):
                result = trainer.train_and_save_model()
                if not result['success']:
                    raise UserError(f"Échec entraînement: {result['error']}")

            # 2. Puis mettre à jour les prédictions
            partners = self.env['res.partner'].search([
                ('last_purchase_date', '!=', False),
                ('total_sales', '>', 0)
            ], limit=self.batch_size)

            if partners:
                partners._predict_ml_metrics()
                self.processed_partners = len(partners)

            return True

        except Exception as e:
            _logger.exception("Échec cron prédictions")
            raise

    def action_test_cron(self):
        """Méthode pour tester manuellement"""
        self._cron_update_predictions()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Succès',
                'message': f'{self.processed_partners} clients mis à jour',
                'sticky': False,
            }
        }