/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.CartLoyaltyManager = publicWidget.Widget.extend({
    selector: '#cart_products',
    events: {
        'change .js_quantity': '_onQtyChange',
        'click .js_add_cart_json': '_onAddRemove',
        'click .js_add_to_cart': '_onAddToCart',
    },

    init: function() {
        this._super.apply(this, arguments);
        this._forcedDiscount = null;
        this._forcedRuleId = null;
    },

    start: function() {
        console.log("[Loyalty] Manager initialized");
        this._checkSuggestions();
        return this._super.apply(this, arguments);
    },

    // Méthodes communes
    _onQtyChange: function(ev) {
        this._updateDiscounts();
        this._checkSuggestions();
    },

    _onAddRemove: function(ev) {
        ev.preventDefault();
        this._updateDiscounts();
        this._checkSuggestions();
        setTimeout(() => $(document).trigger('update_cart'), 1000);
    },

    _onAddToCart: function(ev) {
        setTimeout(() => this._checkSuggestions(), 1000);
    },

    // Gestion des remises unifiée
    _updateDiscounts: function() {
        var self = this;
        var params = this._forcedDiscount ? {
            force_discount: this._forcedDiscount,
            rule_id: this._forcedRuleId
        } : {};

        console.log("[Loyalty] Updating discounts with params:", params);
        this.$el.addClass('o_loading');

        jsonrpc('/shop/cart/update_discounts', params)
            .then(function(result) {
                if (!result.success) throw new Error("Discount update failed");
                return jsonrpc('/shop/cart/update_amounts', {});
            })
            .then(function(amounts) {
                self._updateCartUI(amounts);
                if (self._forcedDiscount) {
                    self._forcedDiscount = null; // Reset après application
                    self._forcedRuleId = null;
                }
            })
            .catch(function(error) {
                console.error("[Loyalty] Error:", error);
                window.location.reload();
            })
            .finally(function() {
                self.$el.removeClass('o_loading');
            });
    },

    // Gestion des suggestions
    _checkSuggestions: function() {
        var self = this;
        var productIds = [];

        $('#cart_products [data-product-id]').each(function() {
            productIds.push(parseInt($(this).data('product-id')));
        });

        if (productIds.length > 0) {
            jsonrpc('/shop/check_product_suggestions', { product_ids: productIds })
                .then(function(result) {
                    if (result.success && result.suggestions.length > 0) {
                        self._showSuggestionConfirm(result.suggestions[0]);
                    }
                });
        }
    },

    _showSuggestionConfirm: function(suggestion) {
        const message = ` Ajoutez "${suggestion.product_name}" pour bénéficier de la carte "${suggestion.card_name}" liée au programme "${suggestion.loyalty_program_name}"  offrant une remise de ${suggestion.reward_discount}% ?`;
        if (window.confirm(message)) {
            this._applySuggestion(suggestion.rule_id);
        }
    },

_applySuggestion: function(ruleId) {
    var self = this;
    this.$el.addClass('o_loading');

    jsonrpc('/shop/apply_product_suggestion', { rule_id: ruleId })
        .then(function(result) {
            if (result.success) {
                // Applique la remise forcée temporairement
                self._forcedDiscount = result.suggestion_discount;
                self._forcedRuleId = result.rule_id;
                return self._updateDiscounts();
            }
        })
        .then(function() {
            // Déclenche la mise à jour dynamique du panier
            window.location.reload();
            $(document).trigger('update_cart');
        })
        .finally(() => this.$el.removeClass('o_loading'));
},

    // Mise à jour de l'interface
    _updateCartUI: function(amounts) {
        var displayDiscount = amounts.forced_discount || Object.values(amounts.discounts)[0];

        // Mise à jour des totaux
        $('.oe_currency_value').each(function() {
            var $elem = $(this);
            var fieldName = $elem.data('field-name');
            if (fieldName && amounts[fieldName] !== undefined) {
                $elem.text(amounts[fieldName]);
            }
        });

        // Mise à jour des remises ligne par ligne
        $('.js_product_discount').each(function() {
            var $elem = $(this);
            var lineId = $elem.data('line-id');
            if (lineId && amounts.discounts?.[lineId]) {
                $elem.text(amounts.discounts[lineId] + '%');
            }
        });

        console.log("[Loyalty] UI updated with discount:",
                   this._forcedDiscount || "best discount",
                   "Amounts:", amounts);
    }
});
