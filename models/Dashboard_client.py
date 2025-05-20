from odoo import models, fields, tools

class DashboardPurchaseByCustomer(models.Model):
    _name = 'dashboard.purchase.by.customer'
    _description = 'Quantité des Produits Achetés par Client'
    _auto = False

    partner_id = fields.Many2one('res.partner', string="Client", readonly=True)
    partner_name = fields.Char(string="Nom du Client", readonly=True)
    product_id = fields.Many2one('product.product', string="Produit", readonly=True)
    product_name = fields.Char(string="Nom du Produit", readonly=True)
    total_qty = fields.Float(string="Quantité Totale Achetée", readonly=True)
    source = fields.Selection(
        [('sale', 'Vente'), ('pos', 'Point de Vente')],
        string="Source",
        readonly=True
    )

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW dashboard_purchase_by_customer AS (
            -- Ventes e-commerce
            SELECT 
                so.partner_id,
                rp.name AS partner_name,
                sol.product_id,
                pt.name AS product_name,
                SUM(sol.product_uom_qty) AS total_qty,
                'sale' AS source
            FROM sale_order_line sol
            JOIN sale_order so ON so.id = sol.order_id
            JOIN res_partner rp ON rp.id = so.partner_id
            JOIN product_product pp ON pp.id = sol.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN loyalty_reward lr ON lr.id = sol.reward_id  -- Jointure optionnelle
            WHERE so.state IN ('sale', 'done')
              AND sol.reward_id IS NULL  -- Exclure les produits liés à des récompenses
            GROUP BY so.partner_id, rp.name, sol.product_id, pt.name

            UNION ALL

            -- Ventes POS (exclut les lignes de fidélité si applicable)
            SELECT 
                po.partner_id,
                rp.name AS partner_name,
                pol.product_id,
                pt.name AS product_name,
                SUM(pol.qty) AS total_qty,
                'pos' AS source
            FROM pos_order_line pol
            JOIN pos_order po ON po.id = pol.order_id
            JOIN res_partner rp ON rp.id = po.partner_id
            JOIN product_product pp ON pp.id = pol.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN loyalty_reward lr ON lr.id = pol.reward_id  -- Jointure optionnelle pour vérifier les récompenses
            WHERE po.state IN ('paid', 'done', 'invoiced') 
                AND po.partner_id IS NOT NULL
                -- Exclusion spécifique des produits non désirés
                 
                AND pt.sale_ok = TRUE    

            GROUP BY po.partner_id, rp.name, pol.product_id, pt.name
            )
        """)
