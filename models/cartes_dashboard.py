from odoo import models, fields, api, tools

class CarteUsageStats(models.Model):
    _name = 'carte.usage.stats'
    _description = "Statistiques combinées POS et Ventes"
    _auto = False  # Vue SQL

    partner_id = fields.Many2one('res.partner', string="Client")
    carte_id = fields.Many2one('cartes.reduction', string="Carte")
    total_usage = fields.Integer(string="Utilisations Totales")
    pos_usage = fields.Integer(string="Utilisations POS")
    sale_usage = fields.Integer(string="Utilisations Ventes")
    website_usage = fields.Integer(string="Utilisations Web")
    last_use = fields.Date(string="Dernière utilisation")

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW carte_usage_stats AS (
                SELECT 
                    row_number() OVER() AS id,
                    partner_id,
                    carte_id,
                    SUM(usage_count) AS total_usage,
                    SUM(CASE WHEN source = 'pos' THEN usage_count ELSE 0 END) AS pos_usage,
                    SUM(CASE WHEN source = 'sale' THEN usage_count ELSE 0 END) AS sale_usage,
                    SUM(CASE WHEN source = 'website' THEN usage_count ELSE 0 END) AS website_usage,
                    MAX(usage_date) AS last_use
                FROM (
                    -- Données POS
                    SELECT 
                        po.partner_id,
                        cr.id AS carte_id,
                        COUNT(*) AS usage_count,
                        'pos' AS source,
                        MAX(DATE(po.date_order)) AS usage_date
                    FROM pos_order po
                    JOIN pos_order_line pol ON po.id = pol.order_id
                    JOIN cartes_attribution_cartes_reduction_rel rel ON rel.cartes_attribution_id IN (
                        SELECT id FROM cartes_attribution WHERE client_id = po.partner_id
                    )
                    JOIN cartes_reduction cr ON cr.id = rel.cartes_reduction_id
                    WHERE po.state = 'paid' AND po.amount_total > 0  
                    GROUP BY po.partner_id, cr.id

                    UNION ALL

                    -- Données Ventes Web
                    SELECT 
                        so.partner_id,
                        cr.id AS carte_id,
                        COUNT(*) AS usage_count,
                        'website' AS source,
                        MAX(DATE(so.date_order)) AS usage_date
                    FROM sale_order so
                    JOIN sale_order_line sol ON so.id = sol.order_id
                    JOIN cartes_attribution_cartes_reduction_rel rel ON rel.cartes_attribution_id IN (
                        SELECT id FROM cartes_attribution WHERE client_id = so.partner_id
                    )
                    JOIN cartes_reduction cr ON cr.id = rel.cartes_reduction_id
                    WHERE so.state IN ('sale', 'done') 
                    AND so.website_id IS NOT NULL  
                    GROUP BY so.partner_id, cr.id
                    
                    UNION ALL
                    
                    -- Données Ventes Normales (hors web)
                    SELECT 
                        so.partner_id,
                        cr.id AS carte_id,
                        COUNT(*) AS usage_count,
                        'sale' AS source,
                        MAX(DATE(so.date_order)) AS usage_date
                    FROM sale_order so
                    JOIN sale_order_line sol ON so.id = sol.order_id
                    JOIN cartes_attribution_cartes_reduction_rel rel ON rel.cartes_attribution_id IN (
                        SELECT id FROM cartes_attribution WHERE client_id = so.partner_id
                    )
                    JOIN cartes_reduction cr ON cr.id = rel.cartes_reduction_id
                    WHERE so.state IN ('sale', 'done')
                    AND so.website_id IS NULL  
                    GROUP BY so.partner_id, cr.id
                ) AS combined_data
                GROUP BY partner_id, carte_id
            )
        """)