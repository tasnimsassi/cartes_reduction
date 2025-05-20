/** @odoo-module */
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _lt } from "@web/core/l10n/translation";

/**
 * CustomAlertPopup component for displaying custom messages as an alert popup.
 */
export class CustomAlertPopup extends AbstractAwaitablePopup {
    static template = "pos_buttons.CustomAlertPopup";

    static defaultProps = {
        confirmText: _lt("Ok"),
        cancelText: _lt("Cancel"),
        title: _lt("Alert"),
        body: _lt("Something happened"),
    };

    // Quand on clique sur le bouton "Ok"
    async confirm() {
        this.props.resolve(true);

        this.props.close();
    }

    // Quand on clique sur "Cancel" ou fermeture
    cancel() {
        this.props.resolve(false);    // exécute la fonction de rejet si définie
        this.props.close();       // ferme la popup
    }
}
