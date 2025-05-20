from odoo import models, fields, tools

class DashboardProductSales(models.Model):
    _name = 'dashboard.product.sales'
    _description = 'Ventes globales des produits (POS + Sale Order)'
    _auto = False  # Vue SQL matérialisée

    product_id = fields.Many2one('product.product', string="Produit", readonly=True)
    product_name = fields.Char(string="Nom du Produit", readonly=True)
    product_categ_id = fields.Many2one('product.category', string="Catégorie", readonly=True)
    total_qty = fields.Float(string="Quantité Totale Vendue", readonly=True)
    total_revenue = fields.Float(string="Chiffre d'Affaires", readonly=True)
    average_price = fields.Float(string="Prix Moyen", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW dashboard_product_sales AS (
                -- Ventes e-commerce
                SELECT
                    MIN(sol.id) as id,
                    sol.product_id,
                    pt.name as product_name,
                    pt.categ_id as product_categ_id,
                    SUM(sol.product_uom_qty) as total_qty,
                    SUM(sol.price_subtotal) as total_revenue,
                    CASE WHEN SUM(sol.product_uom_qty) > 0 
                         THEN SUM(sol.price_subtotal)/SUM(sol.product_uom_qty) 
                         ELSE 0 END as average_price
                FROM sale_order_line sol
                JOIN product_product pp ON pp.id = sol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN sale_order so ON so.id = sol.order_id
                WHERE 
                    so.state IN ('sale', 'done') AND
                    (sol.discount = 0 OR sol.discount IS NULL) AND  
                    pt.type != 'service' AND
                    sol.price_unit > 0  
                GROUP BY sol.product_id, pt.name, pt.categ_id

                UNION ALL

                -- Ventes POS
                SELECT
                    -MIN(pol.id) as id,
                    pol.product_id,
                    pt.name as product_name,
                    pt.categ_id as product_categ_id,
                    SUM(pol.qty) as total_qty,
                    SUM(pol.price_subtotal) as total_revenue,
                    CASE WHEN SUM(pol.qty) > 0 
                         THEN SUM(pol.price_subtotal)/SUM(pol.qty) 
                         ELSE 0 END as average_price
                FROM pos_order_line pol
                JOIN product_product pp ON pp.id = pol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN pos_order po ON po.id = pol.order_id
                WHERE 
                    po.state IN ('paid', 'done', 'invoiced') AND
                    pt.type != 'service'
                GROUP BY pol.product_id, pt.name, pt.categ_id
            )
        """)
