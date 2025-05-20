from odoo import http
from odoo.http import request


class LoyaltyController(http.Controller):

    @http.route('/sale/order/get_cartes_data', type='json', auth='user')
    def get_cartes_data(self, partner_id):
        sale_order_model = request.env['sale.order']
        result = sale_order_model._get_ui_cartes_data(partner_id)

        partner = request.env['res.partner'].browse(partner_id)
        if partner.exists():
            result.update({
                'id': partner.id,
                'name': partner.name,
            })
        return result
