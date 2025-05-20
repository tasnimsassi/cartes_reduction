import pandas as pd

from odoo import fields, models, api, tools
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
import os
import joblib

from odoo.tools import config

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Relations existantes
    cartes_attribution_ids = fields.One2many(
        'cartes.attribution',
        'client_id',
        string="Cartes attribuées"
    )

    carte_ids = fields.One2many(
        'cartes.attribution',
        'client_id',
        string="Cartes attribuées"
    )

    pos_order_ids = fields.One2many(
        'pos.order',
        'partner_id',
        string="Commandes PoS"
    )

    # Champs existants
    total_sales = fields.Monetary(
        string="Total des Achats",
        compute="_compute_total_sales",
        store=True,
        currency_field="currency_id"
    )

    is_vip = fields.Boolean(
        string="Client VIP",
        compute="_compute_vip_status",
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    # Analyse comportementale
    avg_purchase_value = fields.Float(
        string="Moyenne des Achats",
        compute="_compute_purchase_stats",
        store=True
    )

    purchase_frequency = fields.Float(
        string="Fréquence d'Achat (jours)",
        compute="_compute_purchase_stats",
        store=True
    )

    last_purchase_date = fields.Date(
        string="Dernier Achat",
        compute="_compute_purchase_stats",
        store=True
    )

    customer_segment = fields.Selection([
        ('new', 'Nouveau Client'),
        ('regular', 'Client Régulier'),
        ('vip', 'Client VIP'),
        ('churned', 'Client Inactif')
    ], string="Segment Client", compute="_compute_customer_segment", store=True)

    # Scoring RFM
    recency_score = fields.Integer(
        string="Score Récence",
        compute="_compute_rfm_scores",
        store=True
    )

    frequency_score = fields.Integer(
        string="Score Fréquence",
        compute="_compute_rfm_scores",
        store=True
    )

    monetary_score = fields.Integer(
        string="Score Montant",
        compute="_compute_rfm_scores",
        store=True
    )

    rfm_score = fields.Integer(
        string="Score RFM",
        compute="_compute_rfm_scores",
        store=True
    )

    # Prédictions
    predicted_clv = fields.Float(
        string="Valeur Vie Client Prédite",
        compute="_predict_ml_metrics",
        store=True
    )

    churn_probability = fields.Float(
        string="Probabilité de Désertion",
        compute="_predict_ml_metrics",
        store=True
    )

    next_purchase_prediction = fields.Date(
        string="Date Achat Prédite",
        compute="_predict_ml_metrics",
        store=True
    )

    # Méthodes de base
    @api.depends('pos_order_ids.amount_total')
    def _compute_total_sales(self):
        """Calcule le total des ventes du client"""
        for partner in self:
            pos_orders = self.env['pos.order'].search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['paid', 'done'])
            ])
            partner.total_sales = sum(pos_orders.mapped('amount_total'))

    @api.depends('total_sales')
    def _compute_vip_status(self):
        """Définit un client comme VIP si son total des achats dépasse un seuil"""
        VIP_THRESHOLD = 200  # Seuil augmenté pour un vrai cas VIP
        GOLD_VIP_CARD_PROGRAM = self.env['cartes.reduction'].search([('name', '=', 'Gold_VIP')], limit=1)

        for record in self:
            was_vip = record.is_vip
            record.is_vip = record.total_sales >= VIP_THRESHOLD

            if not was_vip and record.is_vip:
                self._send_vip_notification(record, GOLD_VIP_CARD_PROGRAM)

    def _send_vip_notification(self, partner, card_program):
        """Envoie la notification VIP"""
        mail_values = {
            'subject': f"Félicitations {partner.name} ! Vous êtes désormais VIP 🎉",
            'body_html': f"""
                <div>
                    <p>Bonjour {partner.name},</p>
                    <p>Vous avez atteint le statut <strong>VIP</strong> !</p>
                    <p>Total des achats : <strong>{partner.total_sales:.2f} {partner.currency_id.symbol}</strong></p>
                    <p>Avantages : Carte Gold VIP valable 15 jours</p>
                    <p>L'équipe {self.env.company.name}</p>
                </div>
            """,
            'email_to': partner.email,
            'email_from': self.env.user.email,
        }
        self.env['mail.mail'].create(mail_values).send()

        # Création de la carte VIP
        expiration_date = fields.Datetime.now() + timedelta(days=15)
        self.env['cartes.attribution'].create({
            'client_id': partner.id,
            'carte_ids': [(6, 0, [card_program.id])],
            'date_attribution': fields.Datetime.now(),
            'date_expiration': expiration_date,
            'state': 'validated',
        })

    # Méthodes d'analyse comportementale
    @api.depends('pos_order_ids', 'pos_order_ids.amount_total', 'pos_order_ids.date_order')
    def _compute_purchase_stats(self):
        """Calcule les statistiques d'achat"""
        for partner in self:
            orders = partner.pos_order_ids.filtered(
                lambda o: o.state in ['paid', 'done'] and o.date_order
            )

            # Calcul des métriques de base
            partner.avg_purchase_value = partner.total_sales / len(orders) if orders else 0

            # Calcul de la fréquence
            if len(orders) > 1:
                dates = sorted(orders.mapped('date_order'))
                deltas = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
                partner.purchase_frequency = sum(deltas) / len(deltas) if deltas else 30
            else:
                partner.purchase_frequency = 30  # Valeur par défaut réaliste

            partner.last_purchase_date = max(orders.mapped('date_order')).date() if orders else False

    @api.depends('total_sales', 'last_purchase_date', 'purchase_frequency')
    def _compute_rfm_scores(self):
        """Calcule le score RFM avec des seuils adaptés"""
        for partner in self:
            # Recency (1-5)
            recency = (fields.Date.today() - partner.last_purchase_date).days if partner.last_purchase_date else 365
            partner.recency_score = min(5, max(1, 6 - (recency // 30)))

            # Frequency (1-5)
            freq = partner.purchase_frequency or 30
            partner.frequency_score = min(5, max(1, int(30 / max(1, freq))))  # Évite division par zéro

            # Monetary (1-5) - Seuil ajusté pour les VIP
            monetary = partner.total_sales or 0
            base_amount = 200 if partner.is_vip else 200  # Seuil différent pour les VIP
            partner.monetary_score = min(5, max(1, int(monetary / base_amount)))

            # Score RFM global (100-500)
            partner.rfm_score = (partner.recency_score * 100 +
                                 partner.frequency_score * 10 +
                                 partner.monetary_score)

    @api.depends('rfm_score', 'last_purchase_date')
    def _compute_customer_segment(self):
        """Détermine le segment client avec des règles métiers claires"""
        for partner in self:
            if not partner.last_purchase_date:
                partner.customer_segment = 'new'
            elif (fields.Date.today() - partner.last_purchase_date).days > 90:
                partner.customer_segment = 'churned'
            elif partner.rfm_score >= 450:
                partner.customer_segment = 'vip'
            elif partner.rfm_score >= 300:
                partner.customer_segment = 'regular'
            else:
                partner.customer_segment = 'new'

    # Méthodes de prédiction améliorées (sans ML obligatoire)
    @api.depends('total_sales', 'purchase_frequency', 'last_purchase_date', 'is_vip', 'customer_segment')
    def _predict_metrics(self):
        """Nouvelle méthode unifiée de prédiction avec fallback"""
        for partner in self:
            try:
                # 1. Valeur Vie Client (CLV)
                partner.predicted_clv = self._calculate_clv(partner)

                # 2. Probabilité de Désertion
                partner.churn_probability = self._calculate_churn_prob(partner)

                # 3. Date de prochain achat
                partner.next_purchase_prediction = self._predict_next_purchase(partner)

            except Exception as e:
                _logger.error(f"Erreur prédiction partenaire {partner.id}: {str(e)}")
                partner.update({
                    'predicted_clv': 0,
                    'churn_probability': 0.5,
                    'next_purchase_prediction': False
                })

    def _calculate_clv(self, partner):
        """Calcul basé sur les segments et l'historique"""
        segment_factors = {
            'vip': 2.5,  # Les VIP ont un potentiel 2.5x supérieur
            'regular': 1.2,  # Clients réguliers: 1.2x
            'new': 0.8,  # Nouveaux clients: estimation prudente
            'churned': 0.3  # Clients inactifs: faible potentiel
        }
        return (partner.total_sales or 0) * segment_factors.get(partner.customer_segment, 1.0)

    def _calculate_churn_prob(self, partner):
        """Probabilité basée sur l'activité récente"""
        if not partner.last_purchase_date:
            return 0.9  # 90% si jamais acheté

        inactive_days = (fields.Date.today() - partner.last_purchase_date).days
        freq = partner.purchase_frequency or 30

        # Formule de base
        prob = 0.3  # 30% de base
        prob += inactive_days * 0.005  # +0.5% par jour d'inactivité
        prob -= freq * 0.01  # -1% par jour de fréquence

        # Réduction pour les VIP
        if partner.is_vip:
            prob *= 0.6  # -40% pour les VIP

        return max(0.01, min(0.9, prob))  # Borné entre 1% et 90%

    def _predict_next_purchase(self, partner):
        """Prédiction hybride avec fallback simple"""
        if not partner.last_purchase_date:
            return False

        freq = partner.purchase_frequency or 30

        # Ajustement selon le segment
        segment_adjustment = {
            'vip': 0.7,  # Les VIP reviennent 30% plus vite
            'regular': 1.0,
            'new': 1.3,  # Nouveaux clients prennent plus de temps
            'churned': 2.0  # Clients inactifs reviennent rarement
        }

        adjusted_days = freq * segment_adjustment.get(partner.customer_segment, 1.0)
        return partner.last_purchase_date + timedelta(days=adjusted_days)

    def _get_ml_model(self):
        """Charge le modèle ML si disponible"""
        try:
            model_path = os.path.join(
                tools.config['data_dir'],
                'ml_models',
                'model.pkl'
            )
            if os.path.exists(model_path):
                return joblib.load(model_path)
            return None
        except Exception as e:
            _logger.error(f"Erreur chargement modèle ML: {str(e)}")
            return None

    @api.depends('total_sales', 'purchase_frequency', 'last_purchase_date', 'is_vip', 'customer_segment')
    def _predict_ml_metrics(self):
        model = self._get_ml_model()
        if not model:
            return self._predict_metrics()

        try:
            prediction_data = []
            for partner in self:
                prediction_data.append({
                    'total_sales': partner.total_sales or 0,
                    'purchase_frequency': partner.purchase_frequency or 30,
                    'days_since_last_purchase': (
                                fields.Date.today() - partner.last_purchase_date).days if partner.last_purchase_date else 90,
                    'is_vip': int(partner.is_vip),
                    'customer_segment': {'new': 0, 'regular': 1, 'vip': 2, 'churned': 3}.get(partner.customer_segment,
                                                                                             0)
                })

            df = pd.DataFrame(prediction_data)
            required_features = ['total_sales', 'purchase_frequency', 'days_since_last_purchase', 'is_vip',
                                 'customer_segment']

            predictions = model.predict(df[required_features])

            for i, partner in enumerate(self):
                partner.predicted_clv = float(predictions[i][0])
                partner.churn_probability = float(predictions[i][1])
                partner.next_purchase_prediction = fields.Date.today() + timedelta(days=float(predictions[i][2]))
                _logger.info(f"Partenaire {partner} mis à jour avec les prédictions ML: "
                         f"predicted_clv={partner.predicted_clv}, "
                         f"churn_probability={partner.churn_probability}, "
                         f"next_purchase_prediction={partner.next_purchase_prediction}")
            _logger.info("modifier avec ml ")
            return True
        except Exception as e:
            _logger.error(f"Erreur prédiction ML: {str(e)}")
            return self._predict_metrics()


    def update_behavior_analysis(self):
        """Met à jour toutes les analyses"""
        self._compute_purchase_stats()
        self._compute_rfm_scores()
        self._compute_customer_segment()
        self._predict_ml_metrics()



    def action_test_cron(self):
        # Crée une instance de CustomerMLCron
        cron_model = self.env['customer.ml.cron']
        cron_model.action_test_cron()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Succès',
                'message': f'{cron_model.processed_partners} clients mis à jour',
                'sticky': False,
            }
        }




