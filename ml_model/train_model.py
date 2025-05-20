import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import os
from odoo import api, fields, models, tools, _
import logging
from odoo.exceptions import UserError
import joblib
import os
from odoo.tools import config
from sklearn.multioutput import MultiOutputRegressor

_logger = logging.getLogger(__name__)


class MLModelTrainer(models.Model):
    _name = 'ml.model.trainer'
    _description = 'Entraîneur de modèle ML'

    def _get_partner_data(self):
        partners = self.env['res.partner'].search([
            ('total_sales', '>', 0),
            ('last_purchase_date', '!=', False)
        ])

        data = []
        for p in partners:
            data.append({
                'total_sales': p.total_sales,
                'purchase_frequency': p.purchase_frequency or 30,
                'days_since_last_purchase': (fields.Date.today() - p.last_purchase_date).days,
                'is_vip': int(p.is_vip),
                'customer_segment': {'new': 0, 'regular': 1, 'vip': 2, 'churned': 3}.get(p.customer_segment, 0),
                # Ajoutez les nouvelles cibles pour l'entraînement multi-sortie
                'target_clv': p.total_sales * 2,  # Exemple simple - à adapter
                'target_churn': 0.3 if (fields.Date.today() - p.last_purchase_date).days > 60 else 0.1,
                'target_days_next': self._get_actual_next_purchase_days(p)
            })
        return pd.DataFrame(data)

    def _get_actual_next_purchase_days(self, partner):
        """Calcule les jours jusqu'au prochain achat réel (pour l'entraînement)"""
        orders = self.env['pos.order'].search([
            ('partner_id', '=', partner.id),
            ('date_order', '>=', partner.last_purchase_date)
        ], order='date_order', limit=1)

        if orders:
            return (orders[0].date_order.date() - partner.last_purchase_date).days
        return 30  # Valeur par défaut si pas de nouvel achat

    def train_and_save_model(self):
        try:
            # 1. Chemin du modèle
            model_dir = os.path.join(config['data_dir'], 'ml_models')
            os.makedirs(model_dir, exist_ok=True)
            model_path = os.path.join(model_dir, 'model.pkl')

            # 2. Charger données depuis le CSV initial
            csv_relative_path = os.path.join(os.path.dirname(__file__), '..', 'ml_model', 'dataset_clients.csv')
            csv_path = os.path.abspath(csv_relative_path)
            df_csv = pd.read_csv(csv_path)
            _logger.info("Données CSV chargées depuis %s avec %s lignes", csv_path, len(df_csv))

            # 3. Charger données dynamiques depuis Odoo
            df_odoo = self._get_partner_data()
            _logger.info("Données Odoo récupérées avec %s lignes", len(df_odoo))

            # 4. Fusionner les deux jeux de données
            df = pd.concat([df_csv, df_odoo], ignore_index=True).drop_duplicates()
            _logger.info("Données fusionnées avec %s lignes après suppression des doublons", len(df))

            if len(df) < 3:
                _logger.warning("Données insuffisantes (%s lignes), modèle non généré", len(df))
                return {
                    'success': False,
                    'error': f"Seulement {len(df)} lignes au total (minimum 3 requis)"
                }

            # 5. Entraîner le modèle
            x = df[['total_sales', 'purchase_frequency', 'days_since_last_purchase', 'is_vip', 'customer_segment']]
            y = df[['target_clv', 'target_churn', 'target_days_next']]

            _logger.info("Entraînement du modèle avec %s échantillons", len(df))
            model = MultiOutputRegressor(
                RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
            )
            model.fit(x, y)

            # 6. Sauvegarder le modèle
            joblib.dump(model, model_path)
            _logger.info("Modèle entraîné et sauvegardé dans %s avec %s échantillons", model_path, len(df))

            # 7. Sauvegarder les données mises à jour dans le CSV
            df.to_csv(csv_path, index=False)
            _logger.info("Données Odoo sauvegardées dans le fichier CSV")

            return {
                'success': True,
                'path': model_path,
                'samples': len(df)
            }

        except Exception as e:
            _logger.error("Erreur entraînement : %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }
