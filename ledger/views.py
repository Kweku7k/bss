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
import logging
from datetime import datetime, date

from .models import *
from .forms import *
from .utils import (
    post_journal_entry, generate_trial_balance, generate_balance_sheet,
    generate_profit_loss, generate_ledger_detail
)

# Initialize logger
logger = logging.getLogger('activity')


def _user_can_review_journal(user):
    """Determine if the current user can approve/reject journals."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(
        name__in=['superadmin', 'finance admin']
    ).exists()

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
def csv_account_upload(request):
    """Upload and create accounts from CSV file"""
    if request.method == 'POST':
        from .forms import CSVAccountUploadForm
        form = CSVAccountUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            logger.info(f"CSV Upload started by user: {request.user.username}")
            logger.info(f"File name: {csv_file.name}, Size: {csv_file.size} bytes")
            
            # Decode the file
            try:
                decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
                logger.info(f"Successfully decoded CSV file with {len(decoded_file)} lines")
            except UnicodeDecodeError as e:
                messages.error(request, 'Unable to decode CSV file. Please ensure it is UTF-8 encoded.')
                return redirect('ledger:csv_account_upload')
            
            csv_reader = csv.DictReader(decoded_file)
            
            # Validate headers
            required_headers = {'Code', 'Name', 'Type', 'Currency'}
            optional_headers = {'Parent Code', 'Description'}
            
            # Check if headers exist (case-insensitive)
            if csv_reader.fieldnames:
                headers = {h.strip() for h in csv_reader.fieldnames}
                headers_lower = {h.lower() for h in headers}
                required_lower = {h.lower() for h in required_headers}
                
                missing_headers = required_lower - headers_lower
                if missing_headers:
                    print(f"Missing required columns: {', '.join(missing_headers)}")
                    messages.error(request, f'Missing required columns: {", ".join(missing_headers)}')
                    return redirect('ledger:csv_account_upload')
            else:
                print("CSV file has no headers")
                messages.error(request, 'CSV file appears to be empty or has no headers.')
                return redirect('ledger:csv_account_upload')
            
            # Process CSV rows
            created_count = 0
            updated_count = 0
            errors = []
            row_num = 1
            
            print("Starting to process CSV rows...")
            
            # Create a mapping of lowercase headers to actual headers
            header_map = {h.strip().lower(): h.strip() for h in csv_reader.fieldnames}
            
            for row in csv_reader:
                row_num += 1
                
                # Skip empty rows
                if not any(row.values()):
                    print(f"Row {row_num}: Skipping empty row")
                    continue
                
                try:
                    # Get values using case-insensitive lookup
                    code = row.get(header_map.get('code', '')).strip() if row.get(header_map.get('code', '')) else None
                    name = row.get(header_map.get('name', '')).strip() if row.get(header_map.get('name', '')) else None
                    account_type = row.get(header_map.get('type', '')).strip() if row.get(header_map.get('type', '')) else None
                    currency_code = row.get(header_map.get('currency', '')).strip() if row.get(header_map.get('currency', '')) else None
                    parent_code = row.get(header_map.get('parent code', '')).strip() if row.get(header_map.get('parent code', '')) else None
                    description = row.get(header_map.get('description', '')).strip() if row.get(header_map.get('description', '')) else ''
                    
                    print(f"Row {row_num}: Processing account - Code: {code}, Name: {name}, Type: {account_type}")
                    
                    
                    # Validate required fields
                    if not code:
                        error_msg = f"Row {row_num}: Code is required"
                        errors.append(error_msg)
                        print(error_msg)
                        continue
                    
                    if not name:
                        error_msg = f"Row {row_num}: Name is required"
                        errors.append(error_msg)
                        print(error_msg)
                        continue
                    
                    if not account_type:
                        error_msg = f"Row {row_num}: Type is required"
                        errors.append(error_msg)
                        print(error_msg)
                        continue
                    
                    if not currency_code:
                        error_msg = f"Row {row_num}: Currency is required"
                        errors.append(error_msg)
                        print(error_msg)
                        continue
                    
                    # Validate account type
                    account_type = account_type.upper()
                    valid_types = ['ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE', 'HEADER']
                    if account_type not in valid_types:
                        error_msg = f"Row {row_num}: Invalid account type '{account_type}'. Must be one of: {', '.join(valid_types)}"
                        errors.append(error_msg)
                        print(error_msg)
                        continue
                    
                    # Find currency
                    try:
                        currency = Currency.objects.get(code=currency_code.upper(), is_active=True)
                        print(f"Row {row_num}: Currency '{currency_code}' found")
                    except Currency.DoesNotExist:
                        error_msg = f"Row {row_num}: Currency '{currency_code}' not found or not active"
                        errors.append(error_msg)
                        print(error_msg)
                        continue
                    
                    # Find parent account if specified
                    parent = None
                    if parent_code:
                        try:
                            parent = Account.objects.get(code=parent_code)
                            print(f"Row {row_num}: Parent account '{parent_code}' found")
                        except Account.DoesNotExist:
                            error_msg = f"Row {row_num}: Parent account '{parent_code}' not found"
                            errors.append(error_msg)
                            print(error_msg)
                            continue
                    
                    # Check if account already exists
                    existing_account = Account.objects.filter(code=code).first()
                    
                    if existing_account:
                        # Update existing account
                        existing_account.name = name
                        existing_account.type = account_type
                        existing_account.parent = parent
                        existing_account.currency = currency
                        existing_account.description = description
                        existing_account.save()
                        updated_count += 1
                        print(f"Row {row_num}: Updated account {code} - {name}")
                    else:
                        # Create new account
                        Account.objects.create(
                            code=code,
                            name=name,
                            type=account_type,
                            parent=parent,
                            currency=currency,
                            description=description,
                            created_by=request.user,
                            is_active=True
                        )
                        created_count += 1
                        print(f"Row {row_num}: Created account {code} - {name}")
                
                except Exception as e:
                    error_msg = f"Row {row_num}: {str(e)}"
                    errors.append(error_msg)
                    print(f"Row {row_num}: Exception occurred - {str(e)}")
            
            # Display results
            logger.info(f"CSV Upload completed: Created={created_count}, Updated={updated_count}, Errors={len(errors)}")
            
            if created_count > 0:
                messages.success(request, f'Successfully created {created_count} account(s).')
                print(f"Successfully created {created_count} account(s)")
            
            if updated_count > 0:
                messages.info(request, f'Updated {updated_count} existing account(s).')
                print(f"Updated {updated_count} existing account(s)")
            
            if errors:
                print(f"Total errors encountered: {len(errors)}")
                for error in errors[:10]:  # Show first 10 errors
                    messages.error(request, error)
                
                if len(errors) > 10:
                    messages.error(request, f'... and {len(errors) - 10} more errors.')
                    print(f"Showing first 10 errors out of {len(errors)} total errors")
            
            if created_count > 0 or updated_count > 0:
                print("Redirecting to chart of accounts page")
                return redirect('ledger:chart_of_accounts')
            else:
                print("No accounts created or updated. Staying on upload page")
    else:
        from .forms import CSVAccountUploadForm
        form = CSVAccountUploadForm()
    
    context = {
        'form': form,
        'title': 'Upload Chart of Accounts (CSV)',
    }
    return render(request, 'ledger/csv_account_upload.html', context)


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
    journals = (
        Journal.objects.select_related(
            'created_by',
            'submitted_by',
            'approved_by',
            'posted_by'
        )
        .prefetch_related('lines')
        .order_by('-date', '-created_at')
    )
    
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
    base_currency = Currency.objects.filter(is_base_currency=True).first()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'source_module': source_module,
        'status_choices': Journal._meta.get_field('status').choices,
        'source_choices': Journal._meta.get_field('source_module').choices,
        'base_currency': base_currency,
        'can_review': _user_can_review_journal(request.user),
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
    base_currency = Currency.objects.filter(is_base_currency=True).first()
    comments = journal.comments.select_related('author').all()
    approvals = journal.approvals.select_related('actor').all()
    comment_form = JournalCommentForm()
    approval_form = JournalApprovalForm()
    can_review = _user_can_review_journal(request.user)
    
    context = {
        'journal': journal,
        'lines': lines,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'total_base_debit': total_base_debit,
        'total_base_credit': total_base_credit,
        'is_balanced': journal.is_balanced(),
        'balance_difference': total_base_debit - total_base_credit,
        'entered_difference': total_debit - total_credit,
        'unique_currencies': unique_currencies,
        'base_currency': base_currency,
        'comments': comments,
        'approvals': approvals,
        'comment_form': comment_form,
        'approval_form': approval_form,
        'can_review': can_review,
    }
    return render(request, 'ledger/journal_detail.html', context)


@login_required
def journal_create(request):
    """Create a new journal entry with multi-currency support"""
    if request.method == 'POST':
        form = JournalForm(request.POST)
        formset = JournalLineFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    journal = form.save(commit=False)
                    journal.created_by = request.user
                    journal.save()
                    
                    # Get base currency
                    base_currency = Currency.objects.filter(is_base_currency=True).first()
                    
                    # Save journal lines with proper exchange rates
                    for line_form in formset:
                        if line_form.cleaned_data and not line_form.cleaned_data.get('DELETE', False):
                            line = line_form.save(commit=False)
                            line.journal = journal
                            
                            # Get or set exchange rate
                            if line.currency:
                                if base_currency and line.currency != base_currency:
                                    # Get exchange rate for journal date
                                    exchange_rate = ExchangeRate.get_rate(
                                        line.currency, 
                                        base_currency, 
                                        journal.date
                                    )
                                    if exchange_rate:
                                        line.exchange_rate = exchange_rate
                                    else:
                                        # No exchange rate found, use the one from form if provided
                                        if not line.exchange_rate or line.exchange_rate == 0:
                                            raise ValidationError(
                                                f"No exchange rate found for {line.currency.code} to {base_currency.code} on {journal.date}. "
                                                f"Please add the exchange rate first."
                                            )
                                else:
                                    line.exchange_rate = Decimal('1.0')
                            
                            line.save()
                    
                    # Validate that journal is balanced in base currency
                    total_base_debit = sum(line.base_debit for line in journal.lines.all())
                    total_base_credit = sum(line.base_credit for line in journal.lines.all())
                    
                    if abs(total_base_debit - total_base_credit) > Decimal('0.01'):
                        raise ValidationError(
                            f"Journal entries must balance in base currency. "
                            f"Total base debits: {total_base_debit}, Total base credits: {total_base_credit}"
                        )
                    
                    messages.success(request, f'Journal entry {journal.reference_no} created successfully.')
                    return redirect('ledger:journal_detail', journal_id=journal.id)
                    
            except ValidationError as e:
                error_messages = getattr(e, "messages", None)
                if error_messages:
                    for msg in error_messages:
                        messages.error(request, msg)
                else:
                    messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error creating journal entry: {str(e)}')
        else:
            has_errors = False
            if form.errors:
                has_errors = True
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            if formset.errors:
                has_errors = True
                for i, form_errors in enumerate(formset.errors):
                    if form_errors:
                        for field, errors in form_errors.items():
                            for error in errors:
                                messages.error(request, f"Line {i+1} - {field}: {error}")
            non_form_errors = formset.non_form_errors()
            if non_form_errors:
                has_errors = True
                for error in non_form_errors:
                    messages.error(request, error)
            if not has_errors:
                messages.error(
                    request,
                    "Unable to create journal. Please review each line for required values and ensure debits equal credits."
                )
    else:
        form = JournalForm()
        # Create formset with exactly 2 empty forms
        formset = JournalLineFormSet(queryset=JournalLine.objects.none())
    
    # Get base currency and all active currencies for context
    base_currency = Currency.objects.filter(is_base_currency=True).first()
    active_currencies = Currency.objects.filter(is_active=True).order_by('code')
    
    context = {
        'form': form,
        'formset': formset,
        'base_currency': base_currency,
        'active_currencies': active_currencies,
    }
    return render(request, 'ledger/journal_create.html', context)


@login_required
def journal_edit(request, journal_id):
    """Edit an existing journal entry (draft or posted)"""
    journal = get_object_or_404(Journal, id=journal_id)
    
    if request.method == 'POST':
        form = JournalForm(request.POST, instance=journal)
        formset = JournalLineFormSet(request.POST, instance=journal)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    
                    # Get base currency
                    base_currency = Currency.objects.filter(is_base_currency=True).first()
                    
                    # Save journal lines with proper exchange rates
                    for line_form in formset:
                        if line_form.cleaned_data and not line_form.cleaned_data.get('DELETE', False):
                            line = line_form.save(commit=False)
                            line.journal = journal
                            
                            # Get or set exchange rate based on line date
                            line_date = line.date or journal.date
                            if line.currency:
                                if base_currency and line.currency != base_currency:
                                    # Get exchange rate for line date
                                    exchange_rate = ExchangeRate.get_rate(
                                        line.currency, 
                                        base_currency, 
                                        line_date
                                    )
                                    if exchange_rate:
                                        line.exchange_rate = exchange_rate
                                    else:
                                        if not line.exchange_rate or line.exchange_rate == 0:
                                            raise ValidationError(
                                                f"No exchange rate found for {line.currency.code} to {base_currency.code} on {line_date}. "
                                                f"Please add the exchange rate first."
                                            )
                                else:
                                    line.exchange_rate = Decimal('1.0')
                            
                            line.save()
                    
                    # Delete removed lines
                    formset.save()
                    
                    # Validate that journal is balanced in base currency
                    total_base_debit = sum(line.base_debit for line in journal.lines.all())
                    total_base_credit = sum(line.base_credit for line in journal.lines.all())
                    
                    if abs(total_base_debit - total_base_credit) > Decimal('0.01'):
                        raise ValidationError(
                            f"Journal entries must balance in base currency. "
                            f"Total base debits: {total_base_debit}, Total base credits: {total_base_credit}"
                        )
                        
                    messages.success(request, f'Journal entry {journal.reference_no} updated successfully.')
                    return redirect('ledger:journal_detail', journal_id=journal.id)
                    
            except ValidationError as e:
                error_messages = getattr(e, "messages", None)
                if error_messages:
                    for msg in error_messages:
                        messages.error(request, msg)
                else:
                    messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error updating journal entry: {str(e)}')
        else:
            has_errors = False
            if form.errors:
                has_errors = True
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            if formset.errors:
                has_errors = True
                for i, form_errors in enumerate(formset.errors):
                    if form_errors:
                        for field, errors in form_errors.items():
                            for error in errors:
                                messages.error(request, f"Line {i+1} - {field}: {error}")
            non_form_errors = formset.non_form_errors()
            if non_form_errors:
                has_errors = True
                for error in non_form_errors:
                    messages.error(request, error)
            if not has_errors:
                messages.error(
                    request,
                    "Unable to save journal. Please review each line for required values and ensure debits equal credits."
                )
    else:
        form = JournalForm(instance=journal)
        formset = JournalLineFormSet(instance=journal)
    
    # Get base currency and all active currencies for context
    base_currency = Currency.objects.filter(is_base_currency=True).first()
    active_currencies = Currency.objects.filter(is_active=True).order_by('code')
    
    context = {
        'form': form,
        'formset': formset,
        'journal': journal,
        'base_currency': base_currency,
        'active_currencies': active_currencies,
        'is_edit': True,
    }
    return render(request, 'ledger/journal_create.html', context)


@login_required
def journal_post(request, journal_id):
    """Post a journal entry (change status from Draft to Posted)"""
    journal = get_object_or_404(Journal, id=journal_id)
    
    if request.method != 'POST':
        messages.error(request, 'Posting a journal entry requires a POST request.')
        return redirect('ledger:journal_detail', journal_id=journal.id)

    if journal.status not in ['DRAFT', 'APPROVED']:
        messages.error(request, 'Only draft or approved journals can be posted.')
        return redirect('ledger:journal_detail', journal_id=journal.id)
    
    if not journal.is_balanced():
        messages.error(request, 'Cannot post unbalanced journal entry.')
        return redirect('ledger:journal_detail', journal_id=journal.id)
    
    try:
        with transaction.atomic():
            # Post the journal entry
            post_journal_entry(journal, request.user)
            journal.payroll_journals.update(is_posted=True)
            
            messages.success(request, f'Journal entry {journal.reference_no} posted successfully.')
            logger.info(f"Journal {journal.reference_no} posted by {request.user.username}")
            
    except Exception as e:
        messages.error(request, f'Error posting journal entry: {str(e)}')
    
    return redirect('ledger:journal_detail', journal_id=journal.id)


@login_required
def journal_submit_for_approval(request, journal_id):
    journal = get_object_or_404(Journal, id=journal_id)

    if request.method != 'POST':
        return redirect('ledger:journal_detail', journal_id=journal.id)

    try:
        journal.submit_for_approval(request.user)
        messages.success(request, f'Journal entry {journal.reference_no} submitted for approval.')
        logger.info(f"Journal {journal.reference_no} submitted for approval by {request.user.username}")
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'Error submitting journal for approval: {str(e)}')

    return redirect('ledger:journal_detail', journal_id=journal.id)


@login_required
def journal_review(request, journal_id):
    journal = get_object_or_404(Journal, id=journal_id)

    if request.method != 'POST':
        return redirect('ledger:journal_detail', journal_id=journal.id)

    if not _user_can_review_journal(request.user):
        messages.error(request, 'You do not have permission to review journal entries.')
        return redirect('ledger:journal_detail', journal_id=journal.id)

    form = JournalApprovalForm(request.POST)
    if form.is_valid():
        decision = form.cleaned_data['decision']
        comment = form.cleaned_data['comment']

        try:
            if decision == 'approve':
                journal.approve(request.user)
                if comment:
                    JournalComment.objects.create(
                        journal=journal,
                        author=request.user,
                        comment=comment
                    )
                messages.success(request, f'Journal entry {journal.reference_no} approved.')
                logger.info(f"Journal {journal.reference_no} approved by {request.user.username}")
            else:
                journal.reject(request.user, reason=comment)
                messages.warning(request, f'Journal entry {journal.reference_no} rejected.')
                logger.info(f"Journal {journal.reference_no} rejected by {request.user.username}")
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error processing approval decision: {str(e)}')
    else:
        for error in form.errors.values():
            messages.error(request, error)

    return redirect('ledger:journal_detail', journal_id=journal.id)


@login_required
def journal_add_comment(request, journal_id):
    journal = get_object_or_404(Journal, id=journal_id)

    if request.method != 'POST':
        return redirect('ledger:journal_detail', journal_id=journal.id)

    form = JournalCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.journal = journal
        comment.author = request.user
        comment.save()
        messages.success(request, 'Comment added successfully.')
        logger.info(f"Journal {journal.reference_no} comment added by {request.user.username}")
    else:
        for error in form.errors.values():
            messages.error(request, error)

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


@login_required
def api_exchange_rate(request):
    """Get exchange rate for a currency pair on a specific date"""
    from_currency_code = request.GET.get('from_currency')
    to_currency_code = request.GET.get('to_currency')
    as_of_date = request.GET.get('date')
    
    if not all([from_currency_code, to_currency_code, as_of_date]):
        return JsonResponse({
            'error': 'Missing required parameters: from_currency, to_currency, date'
        }, status=400)
    
    try:
        from_currency = Currency.objects.get(code=from_currency_code, is_active=True)
        to_currency = Currency.objects.get(code=to_currency_code, is_active=True)
        
        rate = ExchangeRate.get_rate(from_currency, to_currency, as_of_date)
        
        if rate is None:
            return JsonResponse({
                'error': f'No exchange rate found for {from_currency_code} to {to_currency_code} on {as_of_date}',
                'rate': None
            }, status=404)
        
        return JsonResponse({
            'from_currency': from_currency_code,
            'to_currency': to_currency_code,
            'rate': float(rate),
            'date': as_of_date
        })
        
    except Currency.DoesNotExist as e:
        return JsonResponse({
            'error': f'Currency not found: {str(e)}'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
def api_cost_centers(request):
    """Get list of cost centers (departments and directorates)"""
    from setup.models import Department, Directorate
    
    departments = list(Department.objects.values_list('dept_long_name', flat=True))
    directorates = list(Directorate.objects.values_list('direct_name', flat=True))
    
    cost_centers = sorted(set(departments + directorates))
    
    return JsonResponse({
        'cost_centers': cost_centers
    })


@login_required
def api_account_info(request, account_id):
    """Get account information including currency"""
    try:
        account = Account.objects.select_related('currency').get(id=account_id)
        return JsonResponse({
            'id': account.id,
            'code': account.code,
            'name': account.name,
            'type': account.type,
            'currency': {
                'id': account.currency.id if account.currency else None,
                'code': account.currency.code if account.currency else None,
                'name': account.currency.name if account.currency else None,
            } if account.currency else None,
            'full_name': f"{account.code} - {account.name}"
        })
    except Account.DoesNotExist:
        return JsonResponse({'error': 'Account not found'}, status=404)


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