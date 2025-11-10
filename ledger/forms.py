from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from decimal import Decimal
from .models import *


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'type', 'parent', 'currency', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1000, 1100, 1110',
                'pattern': '[0-9]{4,10}',
                'title': 'Enter 4-10 digit account code'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter account name'
            }),
            'type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'parent': forms.Select(attrs={
                'class': 'form-control'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit parent choices to header accounts or accounts of the same type
        if 'type' in self.data:
            account_type = self.data['type']
            if account_type == 'HEADER':
                self.fields['parent'].queryset = Account.objects.filter(
                    is_active=True, type='HEADER'
                ).exclude(pk=self.instance.pk if self.instance.pk else None)
            else:
                self.fields['parent'].queryset = Account.objects.filter(
                    is_active=True, type='HEADER'
                )
        else:
            self.fields['parent'].queryset = Account.objects.filter(
                is_active=True, type='HEADER'
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
        
        # Limit currency choices to active currencies
        self.fields['currency'].queryset = Currency.objects.filter(is_active=True)

    def clean_code(self):
        code = self.cleaned_data['code']
        if not code.isdigit():
            raise ValidationError("Account code must contain only numbers.")
        
        if len(code) < 4 or len(code) > 10:
            raise ValidationError("Account code must be between 4 and 10 digits.")
            
        if Account.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Account code already exists.")
        return code

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        account_type = cleaned_data.get('type')
        
        # Validate parent-child relationship
        if parent and parent.type == 'HEADER' and account_type != 'HEADER':
            # This is fine - header accounts can have regular accounts as children
            pass
        elif parent and parent.type != 'HEADER' and account_type == 'HEADER':
            raise ValidationError("Header accounts cannot have non-header accounts as parents.")
        
        return cleaned_data


class BulkAccountForm(forms.Form):
    """Form for creating multiple accounts at once"""
    account_data = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Enter account data in CSV format:\nCode,Name,Type,Parent Code,Currency,Description\n1000,Assets,HEADER,,GHS,Root asset category\n1100,Cash,ASSET,1000,GHS,Cash accounts'
        }),
        help_text="Enter account data in CSV format. First row should be headers: Code,Name,Type,Parent Code,Currency,Description"
    )
    
    def clean_account_data(self):
        data = self.cleaned_data['account_data']
        lines = data.strip().split('\n')
        
        if len(lines) < 2:
            raise ValidationError("Please provide at least one account (header row + data row).")
        
        # Validate header row
        headers = [h.strip().lower() for h in lines[0].split(',')]
        required_headers = ['code', 'name', 'type', 'currency']
        for header in required_headers:
            if header not in headers:
                raise ValidationError(f"Missing required header: {header}")
        
        # Validate data rows
        accounts = []
        for i, line in enumerate(lines[1:], 1):
            if not line.strip():
                continue
                
            values = [v.strip() for v in line.split(',')]
            if len(values) != len(headers):
                raise ValidationError(f"Row {i}: Number of values doesn't match headers.")
            
            account_dict = dict(zip(headers, values))
            
            # Validate required fields
            if not account_dict.get('code'):
                raise ValidationError(f"Row {i}: Code is required.")
            if not account_dict.get('name'):
                raise ValidationError(f"Row {i}: Name is required.")
            if not account_dict.get('type'):
                raise ValidationError(f"Row {i}: Type is required.")
            if not account_dict.get('currency'):
                raise ValidationError(f"Row {i}: Currency is required.")
            
            # Validate account type
            valid_types = ['ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE', 'HEADER']
            if account_dict['type'].upper() not in valid_types:
                raise ValidationError(f"Row {i}: Invalid account type. Must be one of: {', '.join(valid_types)}")
            
            # Validate currency
            try:
                Currency.objects.get(code=account_dict['currency'].upper(), is_active=True)
            except Currency.DoesNotExist:
                raise ValidationError(f"Row {i}: Invalid currency code '{account_dict['currency']}'. Currency must exist and be active.")
            
            # Check for duplicate codes
            if account_dict['code'] in [acc['code'] for acc in accounts]:
                raise ValidationError(f"Row {i}: Duplicate account code.")
            
            accounts.append(account_dict)
        
        return accounts


class CSVAccountUploadForm(forms.Form):
    """Form for uploading accounts via CSV file"""
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file with chart of accounts data',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        })
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        # Check file size (5MB limit)
        if csv_file.size > 5 * 1024 * 1024:
            raise ValidationError("File size must not exceed 5MB.")
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            raise ValidationError("Only CSV files are allowed.")
        
        return csv_file


class CurrencyForm(forms.ModelForm):
    class Meta:
        model = Currency
        fields = ['code', 'name', 'symbol', 'decimal_places', 'is_active', 'is_base_currency']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., GHS, USD, EUR',
                'maxlength': '3',
                'style': 'text-transform: uppercase;'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Ghana Cedi, US Dollar'
            }),
            'symbol': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., ₵, $, €'
            }),
            'decimal_places': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '6'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_base_currency': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_code(self):
        code = self.cleaned_data['code']
        if not code.isalpha() or len(code) != 3:
            raise ValidationError("Currency code must be exactly 3 letters.")
        
        if Currency.objects.filter(code=code.upper()).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Currency code already exists.")
        
        return code.upper()

    def clean(self):
        cleaned_data = super().clean()
        is_base_currency = cleaned_data.get('is_base_currency')
        
        if is_base_currency:
            existing_base = Currency.objects.filter(is_base_currency=True).exclude(pk=self.instance.pk)
            if existing_base.exists():
                raise ValidationError("Only one currency can be set as base currency.")
        
        return cleaned_data


class ExchangeRateForm(forms.ModelForm):
    class Meta:
        model = ExchangeRate
        fields = ['from_currency', 'to_currency', 'rate', 'effective_date', 'is_active']
        widgets = {
            'from_currency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'to_currency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'min': '0.000001'
            }),
            'effective_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['from_currency'].queryset = Currency.objects.filter(is_active=True)
        self.fields['to_currency'].queryset = Currency.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        from_currency = cleaned_data.get('from_currency')
        to_currency = cleaned_data.get('to_currency')
        
        if from_currency and to_currency and from_currency == to_currency:
            raise ValidationError("From currency and to currency cannot be the same.")
        
        return cleaned_data


class JournalForm(forms.ModelForm):
    class Meta:
        model = Journal
        fields = ['date', 'source_module']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'source_module': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default source module
        if not self.instance.pk:
            self.fields['source_module'].initial = 'MANUAL'
        
        # Make source_module optional
        self.fields['source_module'].required = False


class JournalLineForm(forms.ModelForm):
    exchange_rate = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control exchange-rate',
            'step': '0.01',
            'readonly': 'readonly'
        })
    )
    
    class Meta:
        model = JournalLine
        fields = ['date', 'account', 'description', 'debit', 'credit', 'currency', 'exchange_rate', 'cost_center']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control line-date',
            }),
            'account': forms.Select(attrs={
                'class': 'form-control select2 account-select',
                'data-placeholder': 'Select Account'
            }),
            'debit': forms.NumberInput(attrs={
                'class': 'form-control debit-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'credit': forms.NumberInput(attrs={
                'class': 'form-control credit-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-control currency-select'
            }),
            'cost_center': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select Cost Center'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Line description (optional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active accounts (exclude HEADER type)
        self.fields['account'].queryset = Account.objects.filter(
            is_active=True
        ).exclude(type='HEADER').select_related('currency').order_by('code')
        
        # Set up currency choices
        self.fields['currency'].queryset = Currency.objects.filter(is_active=True).order_by('code')
        
        # Set default currency to base currency if available
        base_currency = Currency.objects.filter(is_base_currency=True).first()
        if base_currency and not self.instance.pk:
            self.fields['currency'].initial = base_currency
            self.fields['exchange_rate'].initial = Decimal('1.0')
        
        # Get cost centers from departments and directorates
        from setup.models import Department, Directorate
        departments = Department.objects.values_list('dept_long_name', 'dept_long_name')
        directorates = Directorate.objects.values_list('direct_name', 'direct_name')
        cost_center_choices = [('', '-- Select Cost Center --')]
        cost_center_choices.extend(sorted(set(list(departments) + list(directorates)), key=lambda x: x[0]))
        self.fields['cost_center'].widget.choices = cost_center_choices
        
        # Make cost_center required
        self.fields['cost_center'].required = True
        
        # Set default date to today for new lines
        from datetime import date
        if not self.instance.pk:
            self.fields['date'].initial = date.today()

    def clean(self):
        cleaned_data = super().clean()
        debit = cleaned_data.get('debit', 0) or 0
        credit = cleaned_data.get('credit', 0) or 0
        account = cleaned_data.get('account')
        currency = cleaned_data.get('currency')
        cost_center = cleaned_data.get('cost_center')
        
        # If no account is selected, this is an empty form - skip validation
        if not account and debit == 0 and credit == 0:
            # This is a completely empty form - skip all validation
            return cleaned_data
        
        # If account is selected, validate the line
        if account:
            # Validate that line has either debit or credit, not both
            if debit > 0 and credit > 0:
                raise ValidationError("A journal line cannot have both debit and credit amounts.")
            if debit == 0 and credit == 0:
                raise ValidationError("A journal line must have either debit or credit amount.")
            
            # Validate currency is set
            if not currency:
                base_currency = Currency.objects.filter(is_base_currency=True).first()
                if base_currency:
                    cleaned_data['currency'] = base_currency

            exchange_rate = cleaned_data.get('exchange_rate') or Decimal('1')
            if Decimal(exchange_rate) <= 0:
                raise ValidationError("Exchange rate must be greater than zero.")
        
        return cleaned_data


# Create formset for journal lines
class JournalLineFormSetBase(inlineformset_factory(
    Journal, JournalLine, 
    form=JournalLineForm,
    extra=2,  # Start with 2 forms
    can_delete=True,
    min_num=0,  # Don't auto-add minimum forms
    validate_min=False,  # Allow validation to pass even with fewer forms
)):
    
    def clean(self):
        """Custom validation for journal lines"""
        if any(self.errors):
            return
        
        # Count valid forms (non-empty and not marked for deletion)
        valid_forms = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                # Check if form has account and either debit or credit
                account = form.cleaned_data.get('account')
                debit = form.cleaned_data.get('debit', 0)
                credit = form.cleaned_data.get('credit', 0)
                if account and (debit > 0 or credit > 0):
                    valid_forms.append(form)
        
        # Ensure we have at least 2 valid lines for double-entry
        if len(valid_forms) < 2:
            raise ValidationError("At least 2 journal lines are required for double-entry bookkeeping.")
        
        # Check that total debits equal total credits
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        total_base_debit = Decimal('0')
        total_base_credit = Decimal('0')

        for form in valid_forms:
            debit = Decimal(form.cleaned_data.get('debit', 0) or 0)
            credit = Decimal(form.cleaned_data.get('credit', 0) or 0)
            exchange_rate = form.cleaned_data.get('exchange_rate') or Decimal('1')
            if not isinstance(exchange_rate, Decimal):
                exchange_rate = Decimal(str(exchange_rate))

            total_debit += debit
            total_credit += credit
            total_base_debit += debit * exchange_rate
            total_base_credit += credit * exchange_rate
        
        if abs(total_debit - total_credit) > Decimal('0.01'):
            raise ValidationError(f"Journal entries must balance in entered amounts. Total debits: {total_debit}, Total credits: {total_credit}")

        if abs(total_base_debit - total_base_credit) > Decimal('0.01'):
            raise ValidationError(
                f"Journal entries must balance in base currency. "
                f"Base debits: {total_base_debit}, Base credits: {total_base_credit}"
            )

JournalLineFormSet = JournalLineFormSetBase


class JournalCommentForm(forms.ModelForm):
    class Meta:
        model = JournalComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Leave a comment for this journal entry.'
            })
        }

    def clean_comment(self):
        comment = (self.cleaned_data.get('comment') or '').strip()
        if not comment:
            raise ValidationError("Comment cannot be empty.")
        return comment


class JournalApprovalForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[
            ('approve', 'Approve'),
            ('reject', 'Reject')
        ],
        initial='approve',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional: provide context for your decision.'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        comment = (cleaned_data.get('comment') or '').strip()

        if decision == 'reject' and not comment:
            raise ValidationError("A comment is required when rejecting a journal.")

        cleaned_data['comment'] = comment
        return cleaned_data


class PettyCashFundForm(forms.ModelForm):
    class Meta:
        model = PettyCashFund
        fields = ['name', 'account', 'custodian', 'max_amount', 'is_active']
        widgets = {
            'max_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit account choices to asset accounts
        self.fields['account'].queryset = Account.objects.filter(type='ASSET', is_active=True)


class PettyCashVoucherForm(forms.ModelForm):
    class Meta:
        model = PettyCashVoucher
        fields = ['fund', 'date', 'amount', 'currency', 'description', 'purpose', 'receipt_number', 'account']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'purpose': forms.TextInput(attrs={'placeholder': 'Business purpose'}),
            'receipt_number': forms.TextInput(attrs={'placeholder': 'Receipt number if available'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Limit account choices to expense accounts
        self.fields['account'].queryset = Account.objects.filter(type='EXPENSE', is_active=True)
        
        # Limit fund choices to active funds
        self.fields['fund'].queryset = PettyCashFund.objects.filter(is_active=True)
        
        # Limit currency choices to active currencies
        self.fields['currency'].queryset = Currency.objects.filter(is_active=True)
        
        # If user is provided, set as requested_by
        if user and not self.instance.pk:
            self.instance.requested_by = user

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        fund = self.cleaned_data.get('fund')
        
        if fund and amount > fund.current_balance:
            raise ValidationError(f"Amount exceeds available fund balance of {fund.current_balance}")
        
        return amount


class PettyCashReconciliationForm(forms.ModelForm):
    class Meta:
        model = PettyCashReconciliation
        fields = ['fund', 'reconciliation_date', 'physical_cash', 'book_balance', 'notes']
        widgets = {
            'reconciliation_date': forms.DateInput(attrs={'type': 'date'}),
            'physical_cash': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'book_balance': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit fund choices to active funds
        self.fields['fund'].queryset = PettyCashFund.objects.filter(is_active=True)


class TrialBalanceForm(forms.Form):
    """Form for generating trial balance report"""
    as_of_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Generate trial balance as of this date"
    )
    include_zero_balances = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Include accounts with zero balances"
    )


class LedgerReportForm(forms.Form):
    """Form for generating ledger detail report"""
    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True).exclude(type='HEADER'),
        empty_label="Select an account"
    )
    from_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Start date for the report"
    )
    to_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="End date for the report"
    )

    def clean(self):
        cleaned_data = super().clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')
        
        if from_date and to_date and from_date > to_date:
            raise ValidationError("From date cannot be after to date.")
        
        return cleaned_data


class JournalReportForm(forms.Form):
    """Form for generating journal listing report"""
    from_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Start date for the report"
    )
    to_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="End date for the report"
    )
    source_module = forms.ChoiceField(
        choices=[('', 'All Modules')] + Journal._meta.get_field('source_module').choices,
        required=True,
        help_text="Filter by source module"
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Journal._meta.get_field('status').choices,
        required=False,
        help_text="Filter by journal status"
    )

    def clean(self):
        cleaned_data = super().clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')
        
        if from_date and to_date and from_date > to_date:
            raise ValidationError("From date cannot be after to date.")
        
        return cleaned_data


class BalanceSheetForm(forms.Form):
    """Form for generating balance sheet report"""
    as_of_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Generate balance sheet as of this date"
    )


class ProfitLossForm(forms.Form):
    """Form for generating profit & loss report"""
    from_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Start date for the report"
    )
    to_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="End date for the report"
    )

    def clean(self):
        cleaned_data = super().clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')
        
        if from_date and to_date and from_date > to_date:
            raise ValidationError("From date cannot be after to date.")
        
        return cleaned_data


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['name', 'fiscal_year', 'description', 'currency', 'total_budget', 'status']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 2024 Annual Budget'
            }),
            'fiscal_year': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 2024'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'currency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'total_budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].queryset = Currency.objects.filter(is_active=True)

    def clean_fiscal_year(self):
        fiscal_year = self.cleaned_data['fiscal_year']
        if not fiscal_year.isdigit() or len(fiscal_year) != 4:
            raise ValidationError("Fiscal year must be a 4-digit year.")
        return fiscal_year


class BudgetLineForm(forms.ModelForm):
    class Meta:
        model = BudgetLine
        fields = ['account', 'allocated_amount', 'description']
        widgets = {
            'account': forms.Select(attrs={
                'class': 'form-control'
            }),
            'allocated_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = Account.objects.filter(is_active=True).exclude(type='HEADER')


BudgetLineFormSet = inlineformset_factory(
    Budget, BudgetLine, form=BudgetLineForm,
    extra=1, can_delete=True, validate_min=False
)
