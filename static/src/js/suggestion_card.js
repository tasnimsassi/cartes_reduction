/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class CardSuggestionPopup extends AbstractAwaitablePopup {
    static template = "cartes_reduction.CardSuggestionPopup";

    static defaultProps = {
        confirmText: _lt("Ajouter"),
        cancelText: _lt("Ignorer"),
        title: _lt("Suggestion intelligente"),
        body: "",
    };
}

registry.category("pos.popups").add("CardSuggestionPopup", CardSuggestionPopup);
