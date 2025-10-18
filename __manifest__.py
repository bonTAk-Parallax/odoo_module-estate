{
    'name': 'Real Estate',
    'version': '1.0',
    'author': 'Parallax',
    'category': 'Real Estate',
    'summary': 'Manage properties and sales listings',
    'depends': ['base'],
    'data': [
        # 'views/estate_property_views.xml',  # add later
        'security/ir.model.access.csv',
        'views/estate_property_views.xml',
        'views/estate_menus.xml',
        'views/estate_property_types_views.xml',
        'views/estate_property_tag_views.xml',
        'views/estate_property_offer_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
