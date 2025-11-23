from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class WmsCostCenter(models.Model):
    _name = 'wms.cost.center'
    _description = 'WMS Cost Center'
    _order = 'code'

    name = fields.Char('Cost Center Name', required=True)
    code = fields.Char('Cost Center Code', required=True)
    description = fields.Text('Description')
    parent_id = fields.Many2one('wms.cost.center', 'Parent Cost Center', ondelete='cascade')
    child_ids = fields.One2many('wms.cost.center', 'parent_id', 'Child Cost Centers')
    is_active = fields.Boolean('Active', default=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)

    # Financial accounts
    expense_account_id = fields.Many2one('account.account', 'Expense Account')
    revenue_account_id = fields.Many2one('account.account', 'Revenue Account')

    # Budgeting
    budget_amount = fields.Float('Budget Amount', digits='Account')
    budget_currency_id = fields.Many2one('res.currency', 'Budget Currency',
                                         default=lambda self: self.env.company.currency_id)
    current_spending = fields.Float('Current Spending', compute='_compute_current_spending', store=True)

    @api.depends('budget_currency_id')
    def _compute_current_spending(self):
        for center in self:
            # Calculate spending for this cost center from related transactions
            # This is a simplified calculation - in real implementation would be more complex
            center.current_spending = 0.0


class WmsServiceType(models.Model):
    _name = 'wms.service.type'
    _description = 'WMS Service Type'
    _order = 'name'

    name = fields.Char('Service Type', required=True)
    code = fields.Char('Service Code', required=True)
    description = fields.Text('Description')
    category = fields.Selection([
        ('storage', 'Storage'),
        ('handling', 'Handling'),
        ('value_added', 'Value Added Services'),
        ('transport', 'Transport'),
        ('other', 'Other'),
    ], string='Category', required=True)

    # Pricing
    default_rate = fields.Float('Default Rate', digits='Product Price')
    rate_unit = fields.Selection([
        ('day', 'Per Day'),
        ('month', 'Per Month'),
        ('item', 'Per Item'),
        ('pallet', 'Per Pallet'),
        ('kg', 'Per Kg'),
        ('cbm', 'Per CBM'),
        ('hour', 'Per Hour'),
        ('transaction', 'Per Transaction'),
    ], string='Rate Unit', default='day')

    # Accounting
    income_account_id = fields.Many2one('account.account', 'Income Account')
    expense_account_id = fields.Many2one('account.account', 'Expense Account')
    tax_ids = fields.Many2many('account.tax', 'wms_service_tax_rel', 'service_id', 'tax_id', 'Taxes')

    is_active = fields.Boolean('Active', default=True)


class WmsServicePricing(models.Model):
    _name = 'wms.service.pricing'
    _description = 'WMS Service Pricing'
    _order = 'service_type_id, owner_id'

    service_type_id = fields.Many2one('wms.service.type', 'Service Type', required=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    location_id = fields.Many2one('stock.location', 'Location')
    effective_date = fields.Date('Effective Date', required=True, default=fields.Date.context_today)
    expiry_date = fields.Date('Expiry Date')

    # Pricing
    rate = fields.Float('Rate', required=True, digits='Product Price')
    min_charge = fields.Float('Minimum Charge', digits='Product Price')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Conditions
    min_quantity = fields.Float('Minimum Quantity')
    max_quantity = fields.Float('Maximum Quantity')
    is_active = fields.Boolean('Active', default=True)

    @api.constrains('effective_date', 'expiry_date')
    def _check_dates(self):
        for pricing in self:
            if pricing.expiry_date and pricing.effective_date > pricing.expiry_date:
                raise ValidationError(_('Expiry date must be after effective date.'))


class WmsFinancialTransaction(models.Model):
    _name = 'wms.financial.transaction'
    _description = 'WMS Financial Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'transaction_date desc'

    name = fields.Char('Transaction Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    transaction_type = fields.Selection([
        ('storage_fee', 'Storage Fee'),
        ('handling_fee', 'Handling Fee'),
        ('value_added', 'Value Added Service'),
        ('penalty', 'Penalty Fee'),
        ('rebate', 'Rebate'),
        ('adjustment', 'Adjustment'),
        ('cost_allocation', 'Cost Allocation'),
    ], string='Transaction Type', required=True)

    # Link to operations
    related_model = fields.Reference([
        ('stock.picking', 'Stock Picking'),
        ('stock.inventory', 'Stock Inventory'),
        ('wms.quality.control', 'Quality Control'),
        ('wms.return.authorization', 'Return Authorization'),
    ], string='Related To')

    related_id = fields.Char('Related ID')

    # Financial details
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    cost_center_id = fields.Many2one('wms.cost.center', 'Cost Center')
    service_type_id = fields.Many2one('wms.service.type', 'Service Type')

    # Amount
    amount = fields.Float('Amount', required=True, digits='Account')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.company.currency_id)
    tax_amount = fields.Float('Tax Amount', digits='Account')
    total_amount = fields.Float('Total Amount', compute='_compute_total_amount', store=True)

    # Dates
    transaction_date = fields.Date('Transaction Date', required=True, default=fields.Date.context_today)
    posting_date = fields.Date('Posting Date')
    due_date = fields.Date('Due Date')

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Accounting
    journal_id = fields.Many2one('account.journal', 'Journal')
    move_id = fields.Many2one('account.move', 'Account Move')
    is_posted = fields.Boolean('Posted', default=False)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.financial.transaction') or _('New')
        return super().create(vals)

    @api.depends('amount', 'tax_amount')
    def _compute_total_amount(self):
        for transaction in self:
            transaction.total_amount = transaction.amount + transaction.tax_amount

    def action_confirm(self):
        """Confirm the transaction"""
        for transaction in self:
            transaction.status = 'confirmed'

    def action_post(self):
        """Post the transaction to accounting"""
        for transaction in self:
            if transaction.status in ['draft', 'confirmed']:
                transaction.status = 'posted'
                transaction.is_posted = True
                transaction.posting_date = fields.Date.context_today(self)

    def action_cancel(self):
        """Cancel the transaction"""
        for transaction in self:
            if transaction.status in ['draft', 'confirmed']:
                transaction.status = 'cancelled'

    def action_reverse(self):
        """Reverse the transaction"""
        for transaction in self:
            if transaction.status == 'posted' and transaction.move_id:
                # Create a reverse entry
                reverse_vals = transaction.copy_data({
                    'name': f"RV-{transaction.name}",
                    'amount': -transaction.amount,
                    'tax_amount': -transaction.tax_amount,
                    'status': 'posted',
                    'is_posted': True,
                    'posting_date': fields.Date.context_today(self),
                })[0]
                self.create(reverse_vals)


class WmsCostAllocation(models.Model):
    _name = 'wms.cost.allocation'
    _description = 'WMS Cost Allocation'
    _order = 'allocation_date desc'

    name = fields.Char('Allocation Name', required=True)
    allocation_code = fields.Char('Allocation Code', required=True, copy=False, readonly=True,
                                  default=lambda self: _('New'))
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    source_cost_center_id = fields.Many2one('wms.cost.center', 'Source Cost Center', required=True)
    target_cost_center_id = fields.Many2one('wms.cost.center', 'Target Cost Center', required=True)

    # Allocation details
    allocation_date = fields.Date('Allocation Date', required=True, default=fields.Date.context_today)
    allocation_type = fields.Selection([
        ('direct', 'Direct Allocation'),
        ('indirect', 'Indirect Allocation'),
        ('percentage', 'Percentage Allocation'),
        ('fixed_amount', 'Fixed Amount Allocation'),
    ], string='Allocation Type', required=True, default='percentage')

    # Amount
    amount = fields.Float('Amount', digits='Account')
    percentage = fields.Float('Percentage %', digits='Account')

    # Allocation basis
    allocation_basis = fields.Selection([
        ('area', 'Based on Area'),
        ('volume', 'Based on Volume'),
        ('weight', 'Based on Weight'),
        ('time', 'Based on Time'),
        ('revenue', 'Based on Revenue'),
        ('other', 'Other'),
    ], string='Allocation Basis')

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('posted', 'Posted'),
    ], string='Status', default='draft')

    # Accounting
    journal_id = fields.Many2one('account.journal', 'Journal')
    move_id = fields.Many2one('account.move', 'Account Move')
    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('allocation_code', _('New')) == _('New'):
            vals['allocation_code'] = self.env['ir.sequence'].next_by_code('wms.cost.allocation') or _('New')
        return super().create(vals)

    def action_confirm(self):
        """Confirm the cost allocation"""
        for allocation in self:
            allocation.status = 'confirmed'

    def action_post(self):
        """Post the cost allocation"""
        for allocation in self:
            if allocation.status in ['draft', 'confirmed']:
                allocation.status = 'posted'


class WmsFinancialReport(models.Model):
    _name = 'wms.financial.report'
    _description = 'WMS Financial Report'
    _order = 'report_date desc'

    name = fields.Char('Report Name', required=True)
    report_code = fields.Char('Report Code', required=True, copy=False, readonly=True,
                              default=lambda self: _('New'))
    report_date = fields.Date('Report Date', required=True, default=fields.Date.context_today)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)

    # Period
    period_start = fields.Date('Period Start', required=True)
    period_end = fields.Date('Period End', required=True)

    # Financial data
    total_revenue = fields.Float('Total Revenue', compute='_compute_financial_data', store=True)
    total_expenses = fields.Float('Total Expenses', compute='_compute_financial_data', store=True)
    net_income = fields.Float('Net Income', compute='_compute_financial_data', store=True)
    storage_revenue = fields.Float('Storage Revenue', compute='_compute_financial_data', store=True)
    handling_revenue = fields.Float('Handling Revenue', compute='_compute_financial_data', store=True)

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('validated', 'Validated'),
        ('archived', 'Archived'),
    ], string='Status', default='draft')

    # Content
    report_content = fields.Html('Report Content')
    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('report_code', _('New')) == _('New'):
            vals['report_code'] = self.env['ir.sequence'].next_by_code('wms.financial.report') or _('New')
        return super().create(vals)

    @api.depends('period_start', 'period_end', 'owner_id')
    def _compute_financial_data(self):
        for report in self:
            if report.period_start and report.period_end:
                # Get transactions in the period for this owner
                transactions = self.env['wms.financial.transaction'].search([
                    ('transaction_date', '>=', report.period_start),
                    ('transaction_date', '<=', report.period_end),
                    ('owner_id', '=', report.owner_id.id),
                    ('status', '=', 'posted'),
                ])

                # Calculate totals
                report.total_revenue = sum(t.total_amount for t in transactions if t.amount > 0)
                report.total_expenses = abs(sum(t.total_amount for t in transactions if t.amount < 0))
                report.net_income = report.total_revenue - report.total_expenses

                # Calculate specific revenues by service type
                storage_transactions = transactions.filtered(
                    lambda t: t.service_type_id and t.service_type_id.category == 'storage'
                )
                report.storage_revenue = sum(t.total_amount for t in storage_transactions if t.amount > 0)

                handling_transactions = transactions.filtered(
                    lambda t: t.service_type_id and t.service_type_id.category == 'handling'
                )
                report.handling_revenue = sum(t.total_amount for t in handling_transactions if t.amount > 0)
            else:
                report.total_revenue = 0.0
                report.total_expenses = 0.0
                report.net_income = 0.0
                report.storage_revenue = 0.0
                report.handling_revenue = 0.0

    def action_generate_report(self):
        """Generate the financial report"""
        for report in self:
            report.status = 'generated'

    def action_validate_report(self):
        """Validate the financial report"""
        for report in self:
            report.status = 'validated'


class WmsInvoiceIntegration(models.Model):
    _name = 'wms.invoice.integration'
    _description = 'WMS Invoice Integration'
    _order = 'invoice_date desc'

    name = fields.Char('Invoice Number', required=True)
    owner_id = fields.Many2one('wms.owner', 'Owner', required=True)
    related_transactions = fields.Many2many('wms.financial.transaction', 'wms_invoice_transaction_rel', 'invoice_id', 'transaction_id', 'Related Transactions')

    # Invoice details
    invoice_date = fields.Date('Invoice Date', required=True, default=fields.Date.context_today)
    due_date = fields.Date('Due Date', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Amounts
    subtotal = fields.Float('Subtotal', compute='_compute_amounts', store=True)
    tax_amount = fields.Float('Tax Amount', compute='_compute_amounts', store=True)
    total_amount = fields.Float('Total Amount', compute='_compute_amounts', store=True)

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Accounting
    invoice_id = fields.Many2one('account.move', 'Account Invoice')
    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    salesperson_id = fields.Many2one('res.users', 'Salesperson')

    @api.depends('related_transactions')
    def _compute_amounts(self):
        for invoice in self:
            transactions = invoice.related_transactions.filtered(lambda t: t.status == 'posted')
            invoice.subtotal = sum(t.amount for t in transactions)
            invoice.tax_amount = sum(t.tax_amount for t in transactions)
            invoice.total_amount = sum(t.total_amount for t in transactions)

    def action_send_invoice(self):
        """Send the invoice to customer"""
        for invoice in self:
            invoice.status = 'sent'

    def action_mark_paid(self):
        """Mark the invoice as paid"""
        for invoice in self:
            invoice.status = 'paid'

    def action_cancel_invoice(self):
        """Cancel the invoice"""
        for invoice in self:
            invoice.status = 'cancelled'