{
    'name': "Cartes de Réduction",
    'version': '1.0',
    'author': "sassi tasnim ",
    'category': 'Sales',
    'summary': "Gérer les cartes de réduction des clients",
    'depends': ['base', 'sale_management','website' ,'account' , 'point_of_sale','loyalty', 'product','pos_loyalty','sale','sale_loyalty','web','website_sale'],
    'external_dependencies': {
        'python': ['scikit-learn>=1.0.0', 'joblib>=1.0.0', 'pandas>=1.0.0']
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/cartes_reduction_kanban.xml',
        'data/cartes_reduction_data.xml',
        'views/cartes_view.xml',
        'views/loyalty_program_views.xml',
        'views/promotions.xml',
        'views/fidelite.xml',
        'views/notifications.xml',
        'views/rapports.xml',
         'reports/cartes_report.xml',
        'views/product_pricelist_views.xml',
        'views/cartes_dashboard.xml',
        'views/product_template_view_inherit.xml',
        'views/sale_loyalty_templates.xml',
        'views/website.xml',
        'views/dashboard_client.xml',
        'views/dashboard_vente_views.xml',
        'views/dashbboard_product.xml',
        'views/base_menu.xml',


    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'cartes_reduction/static/src/js/suggestion_card.js',
            'cartes_reduction/static/src/js/load_carte_reduction.js',
            'cartes_reduction/static/src/js/pos_buttons.js',
            'cartes_reduction/static/src/js/pos_pop_up.js',
            'cartes_reduction/static/src/xml/custom_discount.xml',
            'cartes_reduction/static/src/xml/reduction_button.xml',
            'cartes_reduction/static/src/xml/pos_pop_up.xml',
            'cartes_reduction/static/src/xml/card_suggestion_popup_templates.xml',


        ],
        'web.assets_backend': [
        ],
        'web.assets_frontend': [

            'cartes_reduction/static/src/js/website_sale.js',



        ],

    },

    'installable': True,
    'application': True,
    'images': ['static/description/icon.png',
               'static/img/idelity_card.png',
               'static/img/loyalty_card.png',
               'static/img/promo_code.png',
               'static/img/pos_integration.png',
                'static/img/website_integration.png',
                'static/img/customer_behavior.png',
                'static/img/association_rules.png',
                'static/img/renew_card.png',
                'static/img/promo_benefit.png',

               ],


}
