from django.forms import ValidationError
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.utils import timezone
from decimal import Decimal
import csv
from datetime import datetime, date

from .models import (
    Currency, ExchangeRate, Account, Journal, JournalLine, LedgerBalance,
    PettyCashFund, PettyCashVoucher, PettyCashReconciliation, Budget, BudgetLine
)
from .forms import (
    AccountForm, BulkAccountForm, CurrencyForm, ExchangeRateForm, JournalForm, JournalLineFormSet, PettyCashFundForm,
    PettyCashVoucherForm, PettyCashReconciliationForm, BudgetForm, BudgetLineFormSet,
    TrialBalanceForm, LedgerReportForm, JournalReportForm,
    BalanceSheetForm, ProfitLossForm
)
from .utils import (
    post_journal_entry, generate_trial_balance, generate_balance_sheet,
    generate_profit_loss, generate_ledger_detail
)


@login_required
def chart_of_accounts(request):
    """Display the chart of accounts with management options"""
    accounts = Account.objects.filter(is_active=True).order_by('code')
    
    # Group accounts by type
    account_types = {}
    for account in accounts:
        if account.type not in account_types:
            account_types[account.type] = []
        account_types[account.type].append(account)
    
    context = {
        'account_types': account_types,
        'total_accounts': accounts.count(),
    }
    return render(request, 'ledger/chart_of_accounts.html', context)


@login_required
def account_create(request):
    """Create a new account"""
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.created_by = request.user
            account.save()
            
            messages.success(request, f'Account {account.code} - {account.name} created successfully.')
            return redirect('ledger:chart_of_accounts')
    else:
        form = AccountForm()
    
    context = {
        'form': form,
        'title': 'Create New Account',
    }
    return render(request, 'ledger/account_form.html', context)


@login_required
def account_edit(request, account_id):
    """Edit an existing account"""
    account = get_object_or_404(Account, id=account_id)
    
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'Account {account.code} - {account.name} updated successfully.')
            return redirect('ledger:chart_of_accounts')
    else:
        form = AccountForm(instance=account)
    
    context = {
        'form': form,
        'account': account,
        'title': f'Edit Account: {account.code} - {account.name}',
    }
    return render(request, 'ledger/account_form.html', context)


@login_required
def account_delete(request, account_id):
    """Delete an account"""
    account = get_object_or_404(Account, id=account_id)
    
    if request.method == 'POST':
        # Check if account has transactions
        if account.journallines.exists():
            messages.error(request, f'Cannot delete account {account.code} - {account.name} because it has transactions.')
            return redirect('ledger:chart_of_accounts')
        
        # Check if account has children
        if account.children.exists():
            messages.error(request, f'Cannot delete account {account.code} - {account.name} because it has child accounts.')
            return redirect('ledger:chart_of_accounts')
        
        account_name = f"{account.code} - {account.name}"
        account.delete()
        messages.success(request, f'Account {account_name} deleted successfully.')
        return redirect('ledger:chart_of_accounts')
    
    context = {
        'account': account,
    }
    return render(request, 'ledger/account_confirm_delete.html', context)


@login_required
def bulk_account_create(request):
    """Create multiple accounts at once"""
    if request.method == 'POST':
        form = BulkAccountForm(request.POST)
        if form.is_valid():
            accounts_data = form.cleaned_data['account_data']
            created_count = 0
            errors = []
            
            for account_data in accounts_data:
                try:
                    # Find parent account if specified
                    parent = None
                    if account_data.get('parent code'):
                        try:
                            parent = Account.objects.get(code=account_data['parent code'])
                        except Account.DoesNotExist:
                            errors.append(f"Parent account {account_data['parent code']} not found for {account_data['code']}")
                            continue
                    
                    # Find currency
                    try:
                        currency = Currency.objects.get(code=account_data['currency'].upper(), is_active=True)
                    except Currency.DoesNotExist:
                        errors.append(f"Currency {account_data['currency']} not found for {account_data['code']}")
                        continue
                    
                    # Create account
                    Account.objects.create(
                        code=account_data['code'],
                        name=account_data['name'],
                        type=account_data['type'].upper(),
                        parent=parent,
                        currency=currency,
                        description=account_data.get('description', ''),
                        created_by=request.user,
                        is_active=True
                    )
                    created_count += 1
                    
                except Exception as e:
                    errors.append(f"Error creating account {account_data['code']}: {str(e)}")
            
            if created_count > 0:
                messages.success(request, f'Successfully created {created_count} accounts.')
            
            if errors:
                for error in errors:
                    messages.error(request, error)
            
            return redirect('ledger:chart_of_accounts')
    else:
        form = BulkAccountForm()
    
    context = {
        'form': form,
        'title': 'Bulk Create Accounts',
    }
    return render(request, 'ledger/bulk_account_form.html', context)


@login_required
def account_detail(request, account_id):
    """Display detailed information about a specific account"""
    account = get_object_or_404(Account, id=account_id)
    balance = account.balance if hasattr(account, 'balance') else None
    
    # Get recent transactions
    recent_transactions = JournalLine.objects.filter(
        account=account
    ).select_related('journal').order_by('-journal__date')[:10]
    
    context = {
        'account': account,
        'balance': balance,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'ledger/account_detail.html', context)


@login_required
def journal_list(request):
    """List all journal entries"""
    journals = Journal.objects.select_related('created_by').order_by('-date', '-created_at')
    
    # Filtering
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    source_module = request.GET.get('source_module', '')
    
    if search:
        journals = journals.filter(
            Q(reference_no__icontains=search) |
            Q(description__icontains=search)
        )
    
    if status:
        journals = journals.filter(status=status)
    
    if source_module:
        journals = journals.filter(source_module=source_module)
    
    # Pagination
    paginator = Paginator(journals, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'source_module': source_module,
        'status_choices': Journal._meta.get_field('status').choices,
        'source_choices': Journal._meta.get_field('source_module').choices,
    }
    return render(request, 'ledger/journal_list.html', context)


@login_required
def journal_detail(request, journal_id):
    """Display detailed information about a specific journal entry"""
    journal = get_object_or_404(Journal, id=journal_id)
    lines = journal.lines.select_related('account', 'currency').all()
    
    # Get unique currencies used in this journal
    unique_currencies = Currency.objects.filter(
        journalline__journal=journal
    ).distinct()
    
    # Calculate totals
    total_debit = journal.get_total_debit()
    total_credit = journal.get_total_credit()
    total_base_debit = sum(line.base_debit for line in lines)
    total_base_credit = sum(line.base_credit for line in lines)
    
    context = {
        'journal': journal,
        'lines': lines,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'total_base_debit': total_base_debit,
        'total_base_credit': total_base_credit,
        'is_balanced': journal.is_balanced(),
        'balance_difference': total_debit - total_credit,
        'unique_currencies': unique_currencies,
    }
    return render(request, 'ledger/journal_detail.html', context)


@login_required
def journal_create(request):
    """Create a new journal entry"""
    if request.method == 'POST':
        form = JournalForm(request.POST)
        formset = JournalLineFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    journal = form.save(commit=False)
                    journal.created_by = request.user
                    journal.save()
                    
                    formset.instance = journal
                    formset.save()
                    
                    # Validate that journal is balanced
                    if not journal.is_balanced():
                        raise ValidationError("Journal entries must balance (total debits = total credits)")
                    
                    messages.success(request, f'Journal entry {journal.reference_no} created successfully.')
                    return redirect('ledger:journal_detail', journal_id=journal.id)
                    
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error creating journal entry: {str(e)}')
    else:
        form = JournalForm()
        formset = JournalLineFormSet()
    
    context = {
        'form': form,
        'formset': formset,
    }
    return render(request, 'ledger/journal_create.html', context)


@login_required
def journal_post(request, journal_id):
    """Post a journal entry (change status from Draft to Posted)"""
    journal = get_object_or_404(Journal, id=journal_id)
    
    if journal.status != 'DRAFT':
        messages.error(request, 'Only draft journals can be posted.')
        return redirect('ledger:journal_detail', journal_id=journal.id)
    
    if not journal.is_balanced():
        messages.error(request, 'Cannot post unbalanced journal entry.')
        return redirect('ledger:journal_detail', journal_id=journal.id)
    
    try:
        with transaction.atomic():
            # Post the journal entry
            post_journal_entry(journal, request.user)
            
            messages.success(request, f'Journal entry {journal.reference_no} posted successfully.')
            
    except Exception as e:
        messages.error(request, f'Error posting journal entry: {str(e)}')
    
    return redirect('ledger:journal_detail', journal_id=journal.id)


@login_required
def petty_cash_funds(request):
    """List all petty cash funds"""
    funds = PettyCashFund.objects.filter(is_active=True).select_related('custodian', 'account')
    
    # Get recent vouchers
    recent_vouchers = PettyCashVoucher.objects.select_related(
        'fund', 'currency', 'requested_by'
    ).order_by('-date')[:10]
    
    context = {
        'funds': funds,
        'recent_vouchers': recent_vouchers,
    }
    return render(request, 'ledger/petty_cash_funds.html', context)


@login_required
def petty_cash_fund_create(request):
    """Create a new petty cash fund"""
    if request.method == 'POST':
        form = PettyCashFundForm(request.POST)
        
        if form.is_valid():
            try:
                fund = form.save(commit=False)
                fund.created_by = request.user
                fund.save()
                
                messages.success(request, f'Petty cash fund {fund.name} created successfully.')
                return redirect('ledger:petty_cash_fund_detail', fund_id=fund.id)
                
            except Exception as e:
                messages.error(request, f'Error creating petty cash fund: {str(e)}')
    else:
        form = PettyCashFundForm()
    
    context = {
        'form': form,
        'title': 'Create Petty Cash Fund',
    }
    return render(request, 'ledger/petty_cash_fund_form.html', context)


@login_required
def petty_cash_fund_replenish(request, fund_id):
    """Replenish a petty cash fund"""
    fund = get_object_or_404(PettyCashFund, id=fund_id)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        try:
            amount = Decimal(amount)
            fund.add_funds(amount)
            messages.success(request, f'Successfully added ${amount} to {fund.name}. New balance: ${fund.current_balance}')
            return redirect('ledger:petty_cash_fund_detail', fund_id=fund.id)
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error replenishing fund: {str(e)}')
    
    context = {
        'fund': fund,
        'max_amount': fund.get_remaining_capacity(),
    }
    return render(request, 'ledger/petty_cash_fund_replenish.html', context)


@login_required
def petty_cash_fund_detail(request, fund_id):
    """Display detailed information about a petty cash fund"""
    fund = get_object_or_404(PettyCashFund, id=fund_id)
    vouchers = fund.vouchers.select_related('requested_by', 'approved_by').order_by('-date')
    
    # Filtering
    status = request.GET.get('status', '')
    if status:
        vouchers = vouchers.filter(status=status)
    
    context = {
        'fund': fund,
        'vouchers': vouchers,
        'status': status,
        'status_choices': PettyCashVoucher._meta.get_field('status').choices,
    }
    return render(request, 'ledger/petty_cash_fund_detail.html', context)


@login_required
def petty_cash_voucher_create(request):
    """Create a new petty cash voucher"""
    if request.method == 'POST':
        form = PettyCashVoucherForm(request.POST, user=request.user)
        
        if form.is_valid():
            try:
                voucher = form.save(commit=False)
                voucher.requested_by = request.user
                voucher.save()
                
                messages.success(request, f'Petty cash voucher {voucher.voucher_no} created successfully.')
                return redirect('ledger:petty_cash_fund_detail', fund_id=voucher.fund.id)
                
            except Exception as e:
                messages.error(request, f'Error creating voucher: {str(e)}')
    else:
        form = PettyCashVoucherForm(user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'ledger/petty_cash_voucher_form.html', context)


@login_required
def petty_cash_voucher_detail(request, voucher_id):
    """Display detailed information about a petty cash voucher"""
    voucher = get_object_or_404(PettyCashVoucher, id=voucher_id)
    
    context = {
        'voucher': voucher,
    }
    return render(request, 'ledger/petty_cash_voucher_detail.html', context)


@login_required
def petty_cash_voucher_approve(request, voucher_id):
    """Approve a petty cash voucher"""
    voucher = get_object_or_404(PettyCashVoucher, id=voucher_id)
    
    if not voucher.can_approve():
        messages.error(request, 'This voucher cannot be approved.')
        return redirect('ledger:petty_cash_fund_detail', fund_id=voucher.fund.id)
    
    try:
        with transaction.atomic():
            # Approve the voucher
            voucher.approve(request.user)
            
            # Create journal entry for the disbursement
            journal = Journal.objects.create(
                date=voucher.date,
                description=f"Petty cash disbursement - {voucher.description}",
                source_module='PETTY_CASH',
                created_by=request.user,
                status='DRAFT'
            )
            
            # Create journal lines
            JournalLine.objects.create(
                journal=journal,
                account=voucher.account,
                debit=voucher.amount,
                description=voucher.description
            )
            
            JournalLine.objects.create(
                journal=journal,
                account=voucher.fund.account,
                credit=voucher.amount,
                description=f"Petty cash disbursement from {voucher.fund.name}"
            )
            
            # Post the journal entry
            post_journal_entry(journal, request.user)
            
            # Update fund balance
            voucher.fund.current_balance -= voucher.amount
            voucher.fund.save()
            
            messages.success(request, f'Voucher {voucher.voucher_no} approved and disbursed successfully.')
            
    except Exception as e:
        messages.error(request, f'Error approving voucher: {str(e)}')
    
    return redirect('ledger:petty_cash_fund_detail', fund_id=voucher.fund.id)


@login_required
def reports_trial_balance(request):
    """Generate trial balance report"""
    if request.method == 'POST':
        form = TrialBalanceForm(request.POST)
        if form.is_valid():
            as_of_date = form.cleaned_data['as_of_date']
            include_zero = form.cleaned_data['include_zero_balances']
            
            trial_balance = generate_trial_balance(as_of_date, include_zero)
            
            context = {
                'form': form,
                'trial_balance': trial_balance,
                'as_of_date': as_of_date,
                'include_zero': include_zero,
            }
            return render(request, 'ledger/reports_trial_balance.html', context)
    else:
        form = TrialBalanceForm()
    
    context = {
        'form': form,
    }
    return render(request, 'ledger/reports_trial_balance.html', context)


@login_required
def reports_ledger_detail(request):
    """Generate ledger detail report"""
    if request.method == 'POST':
        form = LedgerReportForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']
            
            ledger_detail = generate_ledger_detail(account, from_date, to_date)
            
            context = {
                'form': form,
                'ledger_detail': ledger_detail,
                'account': account,
                'from_date': from_date,
                'to_date': to_date,
            }
            return render(request, 'ledger/reports_ledger_detail.html', context)
    else:
        form = LedgerReportForm()
    
    context = {
        'form': form,
    }
    return render(request, 'ledger/reports_ledger_detail.html', context)


@login_required
def reports_journal_listing(request):
    """Generate journal listing report"""
    if request.method == 'POST':
        form = JournalReportForm(request.POST)
        if form.is_valid():
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']
            source_module = form.cleaned_data['source_module']
            status = form.cleaned_data['status']
            
            journals = Journal.objects.filter(
                date__range=[from_date, to_date]
            ).select_related('created_by')
            
            if source_module:
                journals = journals.filter(source_module=source_module)
            if status:
                journals = journals.filter(status=status)
            
            journals = journals.order_by('-date', '-created_at')
            
            context = {
                'form': form,
                'journals': journals,
                'from_date': from_date,
                'to_date': to_date,
                'source_module': source_module,
                'status': status,
            }
            return render(request, 'ledger/reports_journal_listing.html', context)
    else:
        form = JournalReportForm()
    
    context = {
        'form': form,
    }
    return render(request, 'ledger/reports_journal_listing.html', context)


@login_required
def reports_balance_sheet(request):
    """Generate balance sheet report"""
    if request.method == 'POST':
        form = BalanceSheetForm(request.POST)
        if form.is_valid():
            as_of_date = form.cleaned_data['as_of_date']
            
            balance_sheet = generate_balance_sheet(as_of_date)
            
            context = {
                'form': form,
                'balance_sheet': balance_sheet,
                'as_of_date': as_of_date,
            }
            return render(request, 'ledger/reports_balance_sheet.html', context)
    else:
        form = BalanceSheetForm()
    
    context = {
        'form': form,
    }
    return render(request, 'ledger/reports_balance_sheet.html', context)


@login_required
def reports_profit_loss(request):
    """Generate profit & loss report"""
    if request.method == 'POST':
        form = ProfitLossForm(request.POST)
        if form.is_valid():
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']
            
            profit_loss = generate_profit_loss(from_date, to_date)
            
            context = {
                'form': form,
                'profit_loss': profit_loss,
                'from_date': from_date,
                'to_date': to_date,
            }
            return render(request, 'ledger/reports_profit_loss.html', context)
    else:
        form = ProfitLossForm()
    
    context = {
        'form': form,
    }
    return render(request, 'ledger/reports_profit_loss.html', context)


# API Views for AJAX requests
@login_required
def api_parent_accounts(request):
    """Get parent account choices for AJAX requests"""
    account_type = request.GET.get('type', '')
    exclude_id = request.GET.get('exclude', '')
    
    queryset = Account.objects.filter(is_active=True, type='HEADER')
    
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    
    accounts = []
    for account in queryset.order_by('code'):
        accounts.append({
            'id': account.id,
            'code': account.code,
            'name': account.name,
        })
    
    return JsonResponse({'accounts': accounts})


@login_required
def api_fund_balance(request, fund_id):
    """Get current balance for a petty cash fund"""
    fund = get_object_or_404(PettyCashFund, id=fund_id)
    
    return JsonResponse({
        'current_balance': float(fund.current_balance),
        'max_amount': float(fund.max_amount),
        'can_disburse': fund.is_active
    })


# Currency Management Views
@login_required
def currency_list(request):
    """List all currencies"""
    currencies = Currency.objects.all().order_by('code')
    
    context = {
        'currencies': currencies,
    }
    return render(request, 'ledger/currency_list.html', context)


@login_required
def currency_create(request):
    """Create a new currency"""
    if request.method == 'POST':
        form = CurrencyForm(request.POST)
        if form.is_valid():
            currency = form.save()
            messages.success(request, f'Currency {currency.code} - {currency.name} created successfully.')
            return redirect('ledger:currency_list')
    else:
        form = CurrencyForm()
    
    context = {
        'form': form,
        'title': 'Create New Currency',
    }
    return render(request, 'ledger/currency_form.html', context)


@login_required
def currency_edit(request, currency_id):
    """Edit an existing currency"""
    currency = get_object_or_404(Currency, id=currency_id)
    
    if request.method == 'POST':
        form = CurrencyForm(request.POST, instance=currency)
        if form.is_valid():
            form.save()
            messages.success(request, f'Currency {currency.code} - {currency.name} updated successfully.')
            return redirect('ledger:currency_list')
    else:
        form = CurrencyForm(instance=currency)
    
    context = {
        'form': form,
        'currency': currency,
        'title': f'Edit Currency: {currency.code} - {currency.name}',
    }
    return render(request, 'ledger/currency_form.html', context)


@login_required
def exchange_rate_list(request):
    """List all exchange rates"""
    exchange_rates = ExchangeRate.objects.select_related('from_currency', 'to_currency').order_by('-effective_date')
    
    # Filtering
    from_currency = request.GET.get('from_currency', '')
    to_currency = request.GET.get('to_currency', '')
    
    if from_currency:
        exchange_rates = exchange_rates.filter(from_currency__code=from_currency)
    if to_currency:
        exchange_rates = exchange_rates.filter(to_currency__code=to_currency)
    
    context = {
        'exchange_rates': exchange_rates,
        'from_currency': from_currency,
        'to_currency': to_currency,
        'currencies': Currency.objects.filter(is_active=True).order_by('code'),
    }
    return render(request, 'ledger/exchange_rate_list.html', context)


@login_required
def exchange_rate_create(request):
    """Create a new exchange rate"""
    if request.method == 'POST':
        form = ExchangeRateForm(request.POST)
        if form.is_valid():
            exchange_rate = form.save(commit=False)
            exchange_rate.created_by = request.user
            exchange_rate.save()
            messages.success(request, f'Exchange rate {exchange_rate.from_currency.code} to {exchange_rate.to_currency.code} created successfully.')
            return redirect('ledger:exchange_rate_list')
    else:
        form = ExchangeRateForm()
    
    context = {
        'form': form,
        'title': 'Create New Exchange Rate',
    }
    return render(request, 'ledger/exchange_rate_form.html', context)


# Budget Management Views
@login_required
def budget_list(request):
    """List all budgets"""
    budgets = Budget.objects.select_related('currency', 'created_by').order_by('-fiscal_year', '-created_at')
    
    # Filtering
    fiscal_year = request.GET.get('fiscal_year', '')
    status = request.GET.get('status', '')
    
    if fiscal_year:
        budgets = budgets.filter(fiscal_year=fiscal_year)
    if status:
        budgets = budgets.filter(status=status)
    
    context = {
        'budgets': budgets,
        'fiscal_year': fiscal_year,
        'status': status,
        'status_choices': Budget._meta.get_field('status').choices,
    }
    return render(request, 'ledger/budget_list.html', context)


@login_required
def budget_create(request):
    """Create a new budget"""
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        formset = BudgetLineFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                print(form.cleaned_data)
                print(formset.cleaned_data)
                budget = form.save(commit=False)
                budget.created_by = request.user
                budget.save()
                
                # Save budget lines
                formset.instance = budget
                saved_lines = formset.save()
                
                messages.success(request, f'Budget {budget.name} created successfully with {len(saved_lines)} budget lines.')
                return redirect('ledger:budget_detail', budget_id=budget.id)
                
            except Exception as e:
                messages.error(request, f'Error creating budget: {str(e)}')
    else:
        form = BudgetForm()
        formset = BudgetLineFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create New Budget',
    }
    return render(request, 'ledger/budget_form.html', context)


@login_required
def budget_detail(request, budget_id):
    """Display detailed information about a budget"""
    budget = get_object_or_404(Budget, id=budget_id)
    lines = budget.lines.select_related('account').all()
    
    context = {
        'budget': budget,
        'lines': lines,
    }
    return render(request, 'ledger/budget_detail.html', context)


@login_required
def budget_edit(request, budget_id):
    """Edit an existing budget"""
    budget = get_object_or_404(Budget, id=budget_id)
    
    if budget.status not in ['DRAFT']:
        messages.error(request, 'Only draft budgets can be edited.')
        return redirect('ledger:budget_detail', budget_id=budget.id)
    
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget)
        formset = BudgetLineFormSet(request.POST, instance=budget)
        
        if form.is_valid() and formset.is_valid():
            try:
                form.save()
                formset.save()
                
                messages.success(request, f'Budget {budget.name} updated successfully.')
                return redirect('ledger:budget_detail', budget_id=budget.id)
                
            except Exception as e:
                messages.error(request, f'Error updating budget: {str(e)}')
    else:
        form = BudgetForm(instance=budget)
        formset = BudgetLineFormSet(instance=budget)
    
    context = {
        'form': form,
        'formset': formset,
        'budget': budget,
        'title': f'Edit Budget: {budget.name}',
    }
    return render(request, 'ledger/budget_form.html', context)


@login_required
def budget_approve(request, budget_id):
    """Approve a budget"""
    budget = get_object_or_404(Budget, id=budget_id)
    
    if budget.status != 'DRAFT':
        messages.error(request, 'Only draft budgets can be approved.')
        return redirect('ledger:budget_detail', budget_id=budget.id)
    
    if request.method == 'POST':
        try:
            budget.status = 'APPROVED'
            budget.approved_by = request.user
            budget.approved_at = timezone.now()
            budget.save()
            
            messages.success(request, f'Budget {budget.name} approved successfully.')
            return redirect('ledger:budget_detail', budget_id=budget.id)
            
        except Exception as e:
            messages.error(request, f'Error approving budget: {str(e)}')
    
    return redirect('ledger:budget_detail', budget_id=budget.id)


@login_required
def budget_reports(request):
    """Generate budget reports"""
    budgets = Budget.objects.filter(status__in=['APPROVED', 'ACTIVE']).order_by('-fiscal_year')
    
    # Filtering
    fiscal_year = request.GET.get('fiscal_year', '')
    budget_id = request.GET.get('budget', '')
    
    if fiscal_year:
        budgets = budgets.filter(fiscal_year=fiscal_year)
    
    selected_budget = None
    if budget_id:
        try:
            selected_budget = Budget.objects.get(id=budget_id)
        except Budget.DoesNotExist:
            pass
    
    context = {
        'budgets': budgets,
        'selected_budget': selected_budget,
        'fiscal_year': fiscal_year,
        'budget_id': budget_id,
    }
    return render(request, 'ledger/budget_reports.html', context)