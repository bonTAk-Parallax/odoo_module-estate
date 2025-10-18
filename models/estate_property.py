
from odoo import fields, models, api
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero

class estate_property(models.Model):
    _name = "estate.property"
    _description = 'Real Estate Property'
    _sql_constraints = [
    ('check_expected_price_positive',
     'CHECK(expected_price > 0)',
     'The expected price must be strictly positive!'),
    ('check_selling_price_positive',
     'CHECK(selling_price >= 0)',
     'The selling price must be positive!'),
]


    name = fields.Char(default="Unknown", string="Title", required=True)
    description = fields.Text()
    postcode= fields.Char()
    date_availability = fields.Datetime("Available from", copy= False
        , default=lambda self: datetime.now() + relativedelta(months=3))
    expected_price = fields.Float()
    selling_price = fields.Float(readonly=True, copy=False)
    bedroom = fields.Integer("Bedrooms", default=2)
    living_area = fields.Integer("Living Area (sqm)")
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer()

    total_area = fields.Integer(
        string="Total Area",
        compute="_compute_total_area",
        store=True
    )

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for prop in self:
            prop.total_area = (prop.living_area or 0) + (prop.garden_area or 0)

    garden_orientation = fields.Selection(string="Type", 
        selection=[
            ('north', 'North'),
            ('south', 'South'),
            ('east', 'East'),
            ('west', 'West'),
        ]
    )

    @api.onchange('garden')
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = 'north'
        else:
            self.garden_area = 0
            self.garden_orientation = False

    active = fields.Boolean(default=True)

    state = fields.Selection(
    selection=[
        ('new', 'New'),
        ('offer_received', 'Offer Received'),
        ('offer_accepted', 'Offer Accepted'),
        ('sold', 'Sold'),
        ('cancelled', 'Cancelled'),
    ],
    string='Status',
    required=True,
    copy=False,
    default='new',
    )

    property_type_id = fields.Many2one("estate.property.type", string="Property Type")

    salesperson_id = fields.Many2one(
        "res.users",
        string="Salesperson",
        default=lambda self: self.env.user,
    )

    buyer_id = fields.Many2one(
        "res.partner",
        string="Buyer",
        copy=False,
    )

    tag_ids = fields.Many2many("estate.property.tag", string="Tags")

    offer_ids = fields.One2many(
    "estate.property.offer",
    "property_id",
    string="Offers"
    )

    best_price = fields.Float(
        string="Best Offer",
        compute="_compute_best_price",
        store=True
    )

    @api.depends('offer_ids.price')
    def _compute_best_price(self):
        for prop in self:
            if prop.offer_ids:
                prop.best_price = max(prop.offer_ids.mapped('price'))
            else:
                prop.best_price = 0.0

    @api.model
    def action_cancel(self):
        for prop in self:
            if prop.state == 'sold':
                raise UserError("A sold property cannot be cancelled.")
            prop.state = 'cancelled'

    @api.model
    def action_sold(self):
        for prop in self:
            if prop.state == 'cancelled':
                raise UserError("A cancelled property cannot be set as sold.")
            if not prop.selling_price:
                raise UserError("Cannot mark as sold without a selling price.")
            prop.state = 'sold'

    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price(self):
        for prop in self:
        # Skip check if selling_price is zero (no offer accepted yet)
            if float_is_zero(prop.selling_price, precision_digits=2):
                continue

        min_allowed = prop.expected_price * 0.9
        if float_compare(prop.selling_price, min_allowed, precision_digits=2) < 0:
            raise ValidationError(
                "The selling price cannot be lower than 90% of the expected price.")



class estate_property_type(models.Model):
    _name = "estate.property.type"
    _description = "Property Type"
    _sql_constraints = [
    ('unique_property_type_name',
     'UNIQUE(name)',
     'The property type name must be unique!'),
]


    name = fields.Char(required=True)


class estate_property_tag(models.Model):
    _name = "estate.property.tag"
    _description = "Property Tag"
    _sql_constraints = [
    ('unique_tag_name',
     'UNIQUE(name)',
     'The property tag name must be unique!'),
]


    name = fields.Char(required=True)


class estate_property_offer(models.Model):
    _name = "estate.property.offer"
    _description = "Property Offer"
    _sql_constraints = [
    ('check_offer_price_positive',
     'CHECK(price > 0)',
     'The offer price must be strictly positive!'),
]


    price = fields.Float()
    status = fields.Selection(
        selection=[
            ('accepted', 'Accepted'),
            ('refused','Refused')
        ],
        string="Status",
        copy=False
    )
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    property_id = fields.Many2one("estate.property", string="Property", required=True)

    validity = fields.Integer(
        string="Validity (days)",
        default=7
    )


    date_deadline = fields.Date(
        string="Deadline",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
        store=True
    )

    @api.depends('validity', 'create_date')
    def _compute_date_deadline(self):
        for offer in self:
            
            create_date = offer.create_date or fields.Datetime.now()
            offer.date_deadline = (create_date + timedelta(days=offer.validity)).date()

    def _inverse_date_deadline(self):
        for offer in self:
            create_date = offer.create_date or fields.Datetime.now()
            delta = offer.date_deadline - create_date.date()
            offer.validity = delta.days


    @api.model
    def action_accept(self):
        for offer in self:
            if offer.property_id.state in ['sold', 'cancelled']:
                raise UserError("Cannot accept an offer for a sold or cancelled property.")

            # Ensure only one accepted offer per property
            accepted_offers = offer.property_id.offer_ids.filtered(lambda o: o.status == 'accepted')
            if accepted_offers:
                raise UserError("Another offer has already been accepted for this property.")

            offer.status = 'accepted'
            # Update property
            offer.property_id.selling_price = offer.price
            offer.property_id.buyer_id = offer.partner_id
            offer.property_id.state = 'offer_accepted'

    @api.model
    def action_refuse(self):
        for offer in self:
            if offer.status != 'accepted':
                offer.status = 'refused'

