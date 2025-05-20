from odoo import http
from odoo.http import request, route


class DisableStandardLoyaltyReward(http.Controller):

    @route(['/shop/claimreward'], type='http', auth='user', website=True)
    def claim_reward(self, **post):
        # Bloquer ou rediriger toute tentative d'utilisation de récompense standard
        return request.redirect('/shop')
