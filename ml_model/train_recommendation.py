
import pandas as pd
import os
from datetime import timedelta
from odoo import models, fields, tools
from mlxtend.frequent_patterns import apriori, association_rules
import logging
_logger = logging.getLogger(__name__)

class ProductAssociationGenerator(models.Model):
    _name = 'product.association.generator'
    _description = 'Générateur de règles d\'association'

    def _get_historical_data(self):
        # Fichier CSV
        module_path = os.path.dirname(__file__)
        csv_path = os.path.join(module_path, 'dataset_achats.csv')

        # Produits à ignorer
        invalid_products = [
            "Recharger le e-wallet", "Carte-cadeau", "50% sur votre commande", "70% sur test", "test"
        ]

        # Charger les données existantes
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            existing_orders = set(tuple(row) for row in df[['product_1', 'product_2', 'product_3']].values)
        else:
            df = pd.DataFrame(columns=['product_1', 'product_2', 'product_3'])
            existing_orders = set()

        # Rechercher les commandes POS
        orders = self.env['pos.order'].search([('date_order', '>=', fields.Datetime.now() - timedelta(days=365))])

        new_data = []
        for order in orders:
            products = [line.product_id.name for line in order.lines if line.product_id.name not in invalid_products]
            if not products:
                continue
            record = (
                products[0] if len(products) > 0 else '',
                products[1] if len(products) > 1 else '',
                products[2] if len(products) > 2 else ''
            )
            if record not in existing_orders:
                new_data.append({
                    'product_1': record[0],
                    'product_2': record[1],
                    'product_3': record[2]
                })

        # Ajouter et sauvegarder
        if new_data:
            new_df = pd.DataFrame(new_data)
            df = pd.concat([df, new_df], ignore_index=True)
            df.to_csv(csv_path, index=False)

        return df

    def _preprocess_data(self, df):
        # Fusionner les colonnes produits en une liste par ligne (transaction)
        transactions = df.fillna('').values.tolist()

        # Créer une liste de transactions avec uniquement les noms de produits non vides
        transaction_list = [[item for item in transaction if item] for transaction in transactions]

        # Créer une dataframe binaire (one-hot encoded)
        from mlxtend.preprocessing import TransactionEncoder
        te = TransactionEncoder()
        te_ary = te.fit(transaction_list).transform(transaction_list)
        basket = pd.DataFrame(te_ary, columns=te.columns_)

        return basket

    def generate_association_rules(self, min_support=0.01, min_confidence=0.7):
        _logger.info("Début de la génération des règles d'association")

        # Charger les données
        df = self._get_historical_data()

        # Nettoyage des données : transformation en transactions binaires
        basket = self._preprocess_data(df)

        # Générer les itemsets fréquents
        frequent_itemsets = apriori(basket, min_support=min_support, use_colnames=True)

        # Générer les règles d'association
        rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)

        # Filtrer les règles intéressantes
        rules = rules[rules['antecedents'].apply(lambda x: len(x) >= 2)]

        _logger.info(f"Règles générées : {len(rules)}")
        # 🔽 LOG DES RÈGLES
        for _, rule in rules.iterrows():
            antecedents = ', '.join(rule['antecedents'])
            consequents = ', '.join(rule['consequents'])
            support = round(rule['support'] * 100, 2)
            confidence = round(rule['confidence'] * 100, 2)
            _logger.info(f"Règle : {antecedents} => {consequents} | Support : {support}% | Confiance : {confidence}%")

        # Sauvegarder les règles dans Odoo
        self._save_rules_to_odoo(rules)

        _logger.info("Fin de la génération des règles d'association")
        return True

    def _save_rules_to_odoo(self, rules):
        _logger.info("Début de l'enregistrement des règles dans Odoo.")

        product_association = self.env['product.association']
        product_association.search([]).unlink()  # Nettoyer les anciennes règles
        _logger.info("Anciennes règles supprimées.")

        for _, rule in rules.iterrows():
            antecedents = list(rule['antecedents'])
            consequent = list(rule['consequents'])[0]

            # Recherche des produits dans Odoo
            antecedent_products = self.env['product.product'].search([('name', 'in', antecedents)])
            associated_product = self.env['product.product'].search([('name', '=', consequent)], limit=1)

            if antecedent_products and associated_product:
                created = product_association.create({
                    'antecedent_product_ids': [(6, 0, antecedent_products.ids)],
                    'associated_product_id': associated_product.id,
                    'confidence': rule['confidence'] * 100,
                    'support': rule['support'] * 100,
                    'card_id': self._get_appropriate_card(antecedents, consequent)
                })

                antecedent_names = ', '.join(antecedent_products.mapped('name'))
                _logger.info(
                    f"Règle enregistrée : {antecedent_names} => {associated_product.name} | "
                    f"Support : {rule['support'] * 100:.2f}% | Confiance : {rule['confidence'] * 100:.2f}% | "
                    f"ID association : {created.id}"
                )
            else:
                _logger.warning(f"Produits non trouvés pour la règle : {antecedents} => {consequent}")

        _logger.info("Fin de l'enregistrement des règles.")

    def _get_appropriate_card(self, antecedents, consequent):
        product_names = antecedents + [consequent]

        if 'café' in product_names or 'lait' in product_names:
            card = self.env['cartes.reduction'].search([('name', '=', 'card_coffee_addict')], limit=1)
            return card.id if card else False

        return False

