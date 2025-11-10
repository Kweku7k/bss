from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


class Currency(models.Model):
    """
    Currency model for multi-currency support
    """
    code = models.CharField(max_length=3, unique=True, help_text="ISO 4217 currency code (e.g., USD, EUR, GHS)")
    name = models.CharField(max_length=100, help_text="Currency name (e.g., US Dollar, Euro, Ghana Cedi)")
    symbol = models.CharField(max_length=10, help_text="Currency symbol (e.g., $, €, ₵)")
    decimal_places = models.PositiveIntegerField(default=2, help_text="Number of decimal places")
    is_active = models.BooleanField(default=True)
    is_base_currency = models.BooleanField(default=False, help_text="Base currency for the organization")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        # Ensure only one base currency
        if self.is_base_currency:
            existing_base = Currency.objects.filter(is_base_currency=True).exclude(pk=self.pk)
            if existing_base.exists():
                raise ValidationError("Only one currency can be set as base currency.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ExchangeRate(models.Model):
    """
    Exchange rate model for currency conversions
    """
    from_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='from_rates')
    to_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='to_rates')
    rate = models.DecimalField(max_digits=12, decimal_places=6, help_text="Exchange rate")
    effective_date = models.DateField(help_text="Date when this rate becomes effective")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-effective_date']
        unique_together = ['from_currency', 'to_currency', 'effective_date']
        verbose_name = 'Exchange Rate'
        verbose_name_plural = 'Exchange Rates'

    def __str__(self):
        return f"{self.from_currency.code} to {self.to_currency.code}: {self.rate}"

    def clean(self):
        if self.from_currency == self.to_currency:
            raise ValidationError("From currency and to currency cannot be the same.")
    
    @staticmethod
    def get_rate(from_currency, to_currency, as_of_date):
        """
        Get exchange rate for converting from_currency to to_currency on a specific date.
        Returns the rate or None if not found.
        """
        from datetime import datetime
        if isinstance(as_of_date, str):
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        
        # If currencies are the same, return 1
        if from_currency == to_currency:
            return Decimal('1.0')
        
        # Check if from_currency is base currency
        base_currency = Currency.objects.filter(is_base_currency=True).first()
        
        # Look for direct rate on or before the date
        rate_obj = ExchangeRate.objects.filter(
            from_currency=from_currency,
            to_currency=to_currency,
            effective_date__lte=as_of_date,
            is_active=True
        ).order_by('-effective_date').first()
        
        if rate_obj:
            return rate_obj.rate
        
        # Try inverse rate
        inverse_rate = ExchangeRate.objects.filter(
            from_currency=to_currency,
            to_currency=from_currency,
            effective_date__lte=as_of_date,
            is_active=True
        ).order_by('-effective_date').first()
        
        if inverse_rate:
            return Decimal('1.0') / inverse_rate.rate
        
        # Try cross rate through base currency
        if base_currency:
            rate_to_base = ExchangeRate.objects.filter(
                from_currency=from_currency,
                to_currency=base_currency,
                effective_date__lte=as_of_date,
                is_active=True
            ).order_by('-effective_date').first()
            
            rate_from_base = ExchangeRate.objects.filter(
                from_currency=base_currency,
                to_currency=to_currency,
                effective_date__lte=as_of_date,
                is_active=True
            ).order_by('-effective_date').first()
            
            if rate_to_base and rate_from_base:
                return rate_to_base.rate * rate_from_base.rate
        
        return None


# Account Types Choices
ACCOUNT_TYPES = [
    ('ASSET', 'Asset'),
    ('LIABILITY', 'Liability'),
    ('EQUITY', 'Equity'),
    ('INCOME', 'Income'),
    ('EXPENSE', 'Expense'),
    ('HEADER', 'Header Account'),
]

# Journal Status Choices
JOURNAL_STATUS = [
    ('DRAFT', 'Draft'),
    ('PENDING_APPROVAL', 'Pending Approval'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
    ('POSTED', 'Posted'),
    ('CANCELLED', 'Cancelled'),
]

JOURNAL_APPROVAL_ACTIONS = [
    ('SUBMITTED', 'Submitted'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
    ('POSTED', 'Posted'),
]

# Source Module Choices
SOURCE_MODULES = [
    ('FEES', 'Fees Module'),
    ('PAYROLL', 'Payroll Module'),
    ('PROCUREMENT', 'Procurement Module'),
    ('PETTY_CASH', 'Petty Cash Module'),
    ('MANUAL', 'Manual Entry'),
    ('SYSTEM', 'System Generated'),
]


class Account(models.Model):
    """
    Chart of Accounts - Defines all accounts used by the university
    """
    code = models.CharField(max_length=10, unique=True, help_text="Account code (e.g., 1000, 1100)")
    name = models.CharField(max_length=255, help_text="Account name")
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, help_text="Account type")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children', help_text="Parent account for grouping")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, help_text="Account currency", null=True, blank=True)
    description = models.TextField(blank=True, help_text="Account description")
    is_active = models.BooleanField(default=True, help_text="Whether account is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        # Validate that header accounts don't have transactions
        if self.type == 'HEADER' and self.journallines.exists():
            raise ValidationError("Header accounts cannot have transactions")

    def get_balance_type(self):
        """Returns whether account increases with debit or credit"""
        if self.type in ['ASSET', 'EXPENSE']:
            return 'DEBIT'
        return 'CREDIT'

    def get_full_path(self):
        """Returns the full hierarchical path of the account"""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return ' > '.join(path)


class Journal(models.Model):
    """
    Journal Entry - Records accounting events
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_no = models.CharField(max_length=20, unique=True, help_text="Auto-generated reference number")
    date = models.DateField(help_text="Transaction date")
    description = models.TextField(blank=True, null=True, help_text="Transaction description (optional)")
    source_module = models.CharField(max_length=50, choices=SOURCE_MODULES, 
                                    help_text="Module that created this entry")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=JOURNAL_STATUS, default='DRAFT')
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_journals'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_journals'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='posted_journals')

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'

    def __str__(self):
        desc = self.description or ''
        return f"{self.reference_no} - {desc[:50]}"

    @property
    def total_debit(self):
        """Calculate total debit amount from all journal lines"""
        return sum(line.debit for line in self.lines.all())

    @property
    def total_credit(self):
        """Calculate total credit amount from all journal lines"""
        return sum(line.credit for line in self.lines.all())

    @property
    def total_base_debit(self):
        """Calculate total base debit amount from all journal lines"""
        return sum(line.base_debit for line in self.lines.all())

    @property
    def total_base_credit(self):
        """Calculate total base credit amount from all journal lines"""
        return sum(line.base_credit for line in self.lines.all())

    @property
    def balance_difference(self):
        """Calculate the difference between total base debits and credits"""
        return self.total_base_debit - self.total_base_credit

    @property
    def entered_balance_difference(self):
        """Difference between original (entered) debits and credits"""
        return self.total_debit - self.total_credit

    @property
    def unique_currencies(self):
        """Get unique currencies used in this journal"""
        return Currency.objects.filter(journalline__journal=self).distinct()

    def save(self, *args, **kwargs):
        if not self.reference_no:
            # Generate reference number
            prefix = self.source_module[:3].upper()
            last_journal = Journal.objects.filter(reference_no__startswith=prefix).order_by('-id').first()
            if last_journal:
                try:
                    last_num = int(last_journal.reference_no.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1
            self.reference_no = f"{prefix}-{next_num:06d}"
        super().save(*args, **kwargs)

    def clean(self):
        # Validate that journal has balanced entries
        if self.pk:  # Only validate if journal exists
            total_debit = sum(line.debit for line in self.lines.all())
            total_credit = sum(line.credit for line in self.lines.all())
            if abs(total_debit - total_credit) > Decimal('0.01'):  # Allow for small rounding differences
                raise ValidationError("Journal entries must balance (total debits = total credits)")

            total_base_debit = sum(line.base_debit for line in self.lines.all())
            total_base_credit = sum(line.base_credit for line in self.lines.all())
            if abs(total_base_debit - total_base_credit) > Decimal('0.01'):
                raise ValidationError(
                    "Journal entries must balance in base currency (total base debits = total base credits)"
                )

    def get_total_debit(self):
        return sum(line.debit for line in self.lines.all())

    def get_total_credit(self):
        return sum(line.credit for line in self.lines.all())

    def is_balanced(self):
        return abs(self.total_base_debit - self.total_base_credit) <= Decimal('0.01')

    def submit_for_approval(self, user):
        """Move journal to pending approval state."""
        if self.status not in ['DRAFT', 'REJECTED']:
            raise ValidationError("Only draft or rejected journals can be submitted for approval.")
        if not self.is_balanced():
            raise ValidationError("Cannot submit an unbalanced journal for approval.")

        self.status = 'PENDING_APPROVAL'
        self.submitted_at = timezone.now()
        self.submitted_by = user
        self.save(update_fields=['status', 'submitted_at', 'submitted_by', 'updated_at'])
        JournalApproval.objects.create(
            journal=self,
            action='SUBMITTED',
            actor=user,
            comment="Journal submitted for approval."
        )

    def approve(self, user):
        """Approve a journal entry."""
        if self.status != 'PENDING_APPROVAL':
            raise ValidationError("Only journals pending approval can be approved.")
        self.status = 'APPROVED'
        self.approved_at = timezone.now()
        self.approved_by = user
        self.save(update_fields=['status', 'approved_at', 'approved_by', 'updated_at'])
        JournalApproval.objects.create(
            journal=self,
            action='APPROVED',
            actor=user,
            comment="Journal approved."
        )

    def reject(self, user, reason=None):
        """Reject a journal entry."""
        if self.status != 'PENDING_APPROVAL':
            raise ValidationError("Only journals pending approval can be rejected.")
        self.status = 'REJECTED'
        self.approved_at = None
        self.approved_by = None
        self.save(update_fields=['status', 'approved_at', 'approved_by', 'updated_at'])
        JournalApproval.objects.create(
            journal=self,
            action='REJECTED',
            actor=user,
            comment=reason or "Journal rejected."
        )
        if reason:
            JournalComment.objects.create(
                journal=self,
                author=user,
                comment=reason,
                is_system=True
            )


class JournalLine(models.Model):
    """
    Journal Line - Individual debit/credit entries within a journal
    """
    journal = models.ForeignKey(Journal, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='journallines')
    date = models.DateField(help_text="Line transaction date", null=True, blank=True)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0, 
                               validators=[MinValueValidator(0)])
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0, 
                                validators=[MinValueValidator(0)])
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, help_text="Transaction currency", null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=1, 
                                      help_text="Exchange rate to base currency")
    base_debit = models.DecimalField(max_digits=12, decimal_places=2, default=0, 
                                   help_text="Debit amount in base currency")
    base_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0, 
                                    help_text="Credit amount in base currency")
    cost_center = models.CharField(max_length=200, blank=True, null=True, 
                                  help_text="Cost center (Department/Directorate)")
    description = models.TextField(blank=True, help_text="Line description")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Journal Line'
        verbose_name_plural = 'Journal Lines'

    def __str__(self):
        return f"{self.journal.reference_no} - {self.account.name}"

    def clean(self):
        # Validate that line has either debit or credit, not both
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("A journal line cannot have both debit and credit amounts")
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("A journal line must have either debit or credit amount")
        
        # Note: Removed strict currency matching validation to support multi-currency transactions
        # Accounts can receive transactions in any currency with proper exchange rate conversion

    def save(self, *args, **kwargs):
        # Set default currency to base currency if not specified
        if not self.currency:
            base_currency = Currency.objects.filter(is_base_currency=True).first()
            if base_currency:
                self.currency = base_currency
                self.exchange_rate = Decimal('1.0')
        
        if self.exchange_rate:
            self.exchange_rate = Decimal(str(self.exchange_rate)).quantize(Decimal('0.01'))

        # Calculate base currency amounts
        if self.currency and self.exchange_rate:
            self.base_debit = (self.debit * self.exchange_rate).quantize(Decimal('0.01'))
            self.base_credit = (self.credit * self.exchange_rate).quantize(Decimal('0.01'))
        else:
            self.base_debit = self.debit
            self.base_credit = self.credit
        super().save(*args, **kwargs)


class LedgerBalance(models.Model):
    """
    Ledger Balance - Stores cumulative account balances
    """
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='balance')
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, help_text="Balance currency", null=True, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Base currency amounts for reporting
    base_opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    base_total_debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    base_total_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ledger Balance'
        verbose_name_plural = 'Ledger Balances'

    def __str__(self):
        return f"{self.account.name} - Balance"

    @property
    def closing_balance(self):
        """Calculate closing balance based on account type"""
        if self.account.type in ['ASSET', 'EXPENSE']:
            # Assets and Expenses increase with debits
            return self.opening_balance + self.total_debit - self.total_credit
        else:
            # Liabilities, Equity, and Income increase with credits
            return self.opening_balance - self.total_debit + self.total_credit

    @property
    def base_closing_balance(self):
        """Calculate closing balance in base currency"""
        if self.account.type in ['ASSET', 'EXPENSE']:
            return self.base_opening_balance + self.base_total_debit - self.base_total_credit
        else:
            return self.base_opening_balance - self.base_total_debit + self.base_total_credit

    def update_balance(self, debit_amount=0, credit_amount=0, base_debit_amount=0, base_credit_amount=0):
        """Update the balance when new transactions are posted"""
        self.total_debit += Decimal(debit_amount)
        self.total_credit += Decimal(credit_amount)
        self.base_total_debit += Decimal(base_debit_amount)
        self.base_total_credit += Decimal(base_credit_amount)
        self.save()


class JournalApproval(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name='approvals')
    action = models.CharField(max_length=20, choices=JOURNAL_APPROVAL_ACTIONS)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Journal Approval'
        verbose_name_plural = 'Journal Approvals'

    def __str__(self):
        return f"{self.journal.reference_no} - {self.action}"


class JournalComment(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    comment = models.TextField()
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Journal Comment'
        verbose_name_plural = 'Journal Comments'

    def __str__(self):
        author = self.author.get_full_name() if self.author else "System"
        return f"{self.journal.reference_no} - {author}"


class PettyCashFund(models.Model):
    """
    Petty Cash Fund - Manages small cash disbursements
    """
    name = models.CharField(max_length=100, help_text="Fund name (e.g., Main Office Petty Cash)")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, limit_choices_to={'type': 'ASSET'})
    custodian = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Person responsible for the fund")
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Maximum amount allowed in fund")
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_funds')

    class Meta:
        verbose_name = 'Petty Cash Fund'
        verbose_name_plural = 'Petty Cash Funds'

    def __str__(self):
        return f"{self.name} - {self.custodian.get_full_name()}"

    def can_disburse(self, amount):
        """Check if fund can disburse the requested amount"""
        return self.current_balance >= amount and self.is_active

    def add_funds(self, amount):
        """Add funds to the petty cash fund"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if self.current_balance + amount > self.max_amount:
            raise ValueError(f"Adding {amount} would exceed maximum fund amount of {self.max_amount}")
        
        self.current_balance += amount
        self.save()

    def get_remaining_capacity(self):
        """Get remaining capacity in the fund"""
        return self.max_amount - self.current_balance

    def get_utilization_percentage(self):
        """Get fund utilization percentage"""
        if self.max_amount > 0:
            return (self.current_balance / self.max_amount) * 100
        return 0


class PettyCashVoucher(models.Model):
    """
    Petty Cash Voucher - Individual disbursement requests
    """
    VOUCHER_STATUS = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
        ('REJECTED', 'Rejected'),
    ]

    fund = models.ForeignKey(PettyCashFund, on_delete=models.CASCADE, related_name='vouchers')
    voucher_no = models.CharField(max_length=20, unique=True, help_text="Auto-generated voucher number")
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, help_text="Voucher currency", null=True, blank=True)
    description = models.TextField(help_text="Purpose of disbursement")
    purpose = models.CharField(max_length=255, help_text="Business purpose", blank=True)
    receipt_number = models.CharField(max_length=50, blank=True, help_text="Receipt number if available")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, 
                               limit_choices_to={'type': 'EXPENSE'})
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_vouchers')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_vouchers')
    status = models.CharField(max_length=20, choices=VOUCHER_STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Petty Cash Voucher'
        verbose_name_plural = 'Petty Cash Vouchers'

    def __str__(self):
        return f"{self.voucher_no} - {self.description[:30]}"

    def save(self, *args, **kwargs):
        if not self.voucher_no:
            # Generate voucher number
            last_voucher = PettyCashVoucher.objects.filter(
                fund=self.fund
            ).order_by('-id').first()
            if last_voucher:
                try:
                    last_num = int(last_voucher.voucher_no.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1
            self.voucher_no = f"PCV-{self.fund.id}-{next_num:04d}"
        super().save(*args, **kwargs)

    def can_approve(self):
        """Check if voucher can be approved"""
        return (self.status == 'PENDING' and 
                self.fund.can_disburse(self.amount) and 
                self.fund.is_active)

    def approve(self, approved_by):
        """Approve the voucher"""
        if self.can_approve():
            self.status = 'APPROVED'
            self.approved_by = approved_by
            self.approved_at = timezone.now()
            self.save()
            return True
        return False


class PettyCashReconciliation(models.Model):
    """
    Petty Cash Reconciliation - Periodic fund reconciliation
    """
    fund = models.ForeignKey(PettyCashFund, on_delete=models.CASCADE, related_name='reconciliations')
    reconciliation_date = models.DateField()
    physical_cash = models.DecimalField(max_digits=10, decimal_places=2, 
                                      help_text="Actual cash counted")
    book_balance = models.DecimalField(max_digits=10, decimal_places=2, 
                                     help_text="Expected balance from records")
    difference = models.DecimalField(max_digits=10, decimal_places=2, 
                                   help_text="Difference between physical and book")
    notes = models.TextField(blank=True)
    reconciled_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reconciliation_date']
        verbose_name = 'Petty Cash Reconciliation'
        verbose_name_plural = 'Petty Cash Reconciliations'

    def __str__(self):
        return f"{self.fund.name} - {self.reconciliation_date}"

    def save(self, *args, **kwargs):
        self.difference = self.physical_cash - self.book_balance
        super().save(*args, **kwargs)


class Budget(models.Model):
    """
    Budget - Annual budget planning and tracking
    """
    BUDGET_STATUS = [
        ('DRAFT', 'Draft'),
        ('APPROVED', 'Approved'),
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
    ]

    name = models.CharField(max_length=255, help_text="Budget name (e.g., 2024 Annual Budget)")
    fiscal_year = models.CharField(max_length=10, help_text="Fiscal year (e.g., 2024)")
    description = models.TextField(blank=True, help_text="Budget description")
    status = models.CharField(max_length=20, choices=BUDGET_STATUS, default='DRAFT')
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, help_text="Budget currency")
    total_budget = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Total budget amount")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_budgets')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_budgets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fiscal_year', '-created_at']
        verbose_name = 'Budget'
        verbose_name_plural = 'Budgets'
        unique_together = ['fiscal_year', 'name']

    def __str__(self):
        return f"{self.name} ({self.fiscal_year})"

    @property
    def total_allocated(self):
        """Calculate total allocated amount across all budget lines"""
        return sum(line.allocated_amount for line in self.lines.all())

    @property
    def total_spent(self):
        """Calculate total spent amount across all budget lines"""
        return sum(line.spent_amount for line in self.lines.all())

    @property
    def remaining_budget(self):
        """Calculate remaining budget amount"""
        return self.total_budget - self.total_spent

    @property
    def utilization_percentage(self):
        """Calculate budget utilization percentage"""
        if self.total_budget > 0:
            return (self.total_spent / self.total_budget) * 100
        return 0


class BudgetLine(models.Model):
    """
    Budget Line - Individual account budget allocations
    """
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, help_text="Account to budget")
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Budgeted amount")
    description = models.TextField(blank=True, help_text="Budget line description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['account__code']
        verbose_name = 'Budget Line'
        verbose_name_plural = 'Budget Lines'
        unique_together = ['budget', 'account']

    def __str__(self):
        return f"{self.budget.name} - {self.account.code} ({self.allocated_amount})"

    @property
    def spent_amount(self):
        """Calculate actual spent amount for this account"""
        # This would need to be calculated based on actual transactions
        # For now, return 0 - this would be implemented with actual transaction data
        return Decimal('0')

    @property
    def remaining_amount(self):
        """Calculate remaining budget amount"""
        return self.allocated_amount - self.spent_amount

    @property
    def utilization_percentage(self):
        """Calculate utilization percentage for this budget line"""
        if self.allocated_amount > 0:
            return (self.spent_amount / self.allocated_amount) * 100
        return 0