from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, date

from .models import Account, Journal, JournalLine, LedgerBalance


def post_journal_entry(journal, posted_by):
    """
    Post a journal entry by updating ledger balances
    """
    if journal.status != 'DRAFT':
        raise ValueError("Only draft journals can be posted")
    
    if not journal.is_balanced():
        raise ValueError("Journal must be balanced before posting")
    
    with transaction.atomic():
        # Update journal status
        journal.status = 'POSTED'
        journal.posted_by = posted_by
        journal.posted_at = timezone.now()
        journal.save()
        
        # Update ledger balances for each line
        for line in journal.lines.all():
            # Get or create ledger balance for the account
            balance, created = LedgerBalance.objects.get_or_create(
                account=line.account,
                defaults={'opening_balance': Decimal('0')}
            )
            
            # Update the balance
            balance.update_balance(line.debit, line.credit)


def generate_trial_balance(as_of_date, include_zero_balances=False):
    """
    Generate trial balance report as of a specific date
    """
    # Get all active accounts (excluding header accounts)
    accounts = Account.objects.filter(
        is_active=True
    ).exclude(type='HEADER').order_by('code')
    
    trial_balance = []
    total_debit = Decimal('0')
    total_credit = Decimal('0')
    
    for account in accounts:
        # Get ledger balance
        try:
            balance = account.balance
            debit_balance = balance.total_debit
            credit_balance = balance.total_credit
            closing_balance = balance.closing_balance
        except LedgerBalance.DoesNotExist:
            debit_balance = Decimal('0')
            credit_balance = Decimal('0')
            closing_balance = Decimal('0')
        
        # Skip accounts with zero balances if requested
        if not include_zero_balances and closing_balance == 0:
            continue
        
        # Determine debit/credit columns based on account type
        if account.type in ['ASSET', 'EXPENSE']:
            # Assets and expenses increase with debits
            debit_amount = closing_balance if closing_balance > 0 else Decimal('0')
            credit_amount = -closing_balance if closing_balance < 0 else Decimal('0')
        else:
            # Liabilities, equity, and income increase with credits
            debit_amount = -closing_balance if closing_balance < 0 else Decimal('0')
            credit_amount = closing_balance if closing_balance > 0 else Decimal('0')
        
        trial_balance.append({
            'account': account,
            'debit': debit_amount,
            'credit': credit_amount,
            'balance': closing_balance,
        })
        
        total_debit += debit_amount
        total_credit += credit_amount
    
    return {
        'accounts': trial_balance,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'as_of_date': as_of_date,
    }


def generate_balance_sheet(as_of_date):
    """
    Generate balance sheet report as of a specific date
    """
    # Get all active accounts
    accounts = Account.objects.filter(is_active=True).exclude(type='HEADER')
    
    assets = []
    liabilities = []
    equity = []
    
    total_assets = Decimal('0')
    total_liabilities = Decimal('0')
    total_equity = Decimal('0')
    
    for account in accounts:
        try:
            balance = account.balance
            closing_balance = balance.closing_balance
        except LedgerBalance.DoesNotExist:
            closing_balance = Decimal('0')
        
        if closing_balance == 0:
            continue
        
        account_data = {
            'account': account,
            'balance': closing_balance,
        }
        
        if account.type == 'ASSET':
            assets.append(account_data)
            total_assets += closing_balance
        elif account.type == 'LIABILITY':
            liabilities.append(account_data)
            total_liabilities += closing_balance
        elif account.type == 'EQUITY':
            equity.append(account_data)
            total_equity += closing_balance
    
    return {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'as_of_date': as_of_date,
    }


def generate_profit_loss(from_date, to_date):
    """
    Generate profit & loss report for a date range
    """
    # Get income and expense accounts
    income_accounts = Account.objects.filter(type='INCOME', is_active=True)
    expense_accounts = Account.objects.filter(type='EXPENSE', is_active=True)
    
    income_items = []
    expense_items = []
    
    total_income = Decimal('0')
    total_expenses = Decimal('0')
    
    # Calculate income
    for account in income_accounts:
        try:
            balance = account.balance
            # For P&L, we want the credit balance (income increases with credits)
            income_amount = balance.total_credit - balance.total_debit
        except LedgerBalance.DoesNotExist:
            income_amount = Decimal('0')
        
        if income_amount > 0:
            income_items.append({
                'account': account,
                'amount': income_amount,
            })
            total_income += income_amount
    
    # Calculate expenses
    for account in expense_accounts:
        try:
            balance = account.balance
            # For P&L, we want the debit balance (expenses increase with debits)
            expense_amount = balance.total_debit - balance.total_credit
        except LedgerBalance.DoesNotExist:
            expense_amount = Decimal('0')
        
        if expense_amount > 0:
            expense_items.append({
                'account': account,
                'amount': expense_amount,
            })
            total_expenses += expense_amount
    
    net_profit = total_income - total_expenses
    
    return {
        'income_items': income_items,
        'expense_items': expense_items,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'from_date': from_date,
        'to_date': to_date,
    }


def generate_ledger_detail(account, from_date, to_date):
    """
    Generate ledger detail report for a specific account and date range
    """
    # Get all journal lines for the account within the date range
    lines = JournalLine.objects.filter(
        account=account,
        journal__date__range=[from_date, to_date],
        journal__status='POSTED'
    ).select_related('journal').order_by('journal__date', 'journal__created_at')
    
    # Calculate running balance
    try:
        opening_balance = account.balance.opening_balance
    except LedgerBalance.DoesNotExist:
        opening_balance = Decimal('0')
    
    ledger_detail = []
    running_balance = opening_balance
    
    for line in lines:
        # Update running balance
        if account.type in ['ASSET', 'EXPENSE']:
            running_balance += line.debit - line.credit
        else:
            running_balance += line.credit - line.debit
        
        ledger_detail.append({
            'line': line,
            'journal': line.journal,
            'running_balance': running_balance,
        })
    
    return {
        'account': account,
        'opening_balance': opening_balance,
        'closing_balance': running_balance,
        'lines': ledger_detail,
        'from_date': from_date,
        'to_date': to_date,
    }


def create_opening_balance_journal(account, amount, created_by):
    """
    Create a journal entry for opening balance
    """
    with transaction.atomic():
        # Create journal
        journal = Journal.objects.create(
            date=date.today(),
            description=f"Opening balance for {account.name}",
            source_module='SYSTEM',
            created_by=created_by,
            status='POSTED'
        )
        
        # Create journal lines
        if account.type in ['ASSET', 'EXPENSE']:
            # Assets and expenses increase with debits
            JournalLine.objects.create(
                journal=journal,
                account=account,
                debit=amount,
                description="Opening balance"
            )
            
            # Create corresponding equity entry
            equity_account = Account.objects.filter(type='EQUITY', is_active=True).first()
            if equity_account:
                JournalLine.objects.create(
                    journal=journal,
                    account=equity_account,
                    credit=amount,
                    description=f"Opening balance for {account.name}"
                )
        else:
            # Liabilities, equity, and income increase with credits
            JournalLine.objects.create(
                journal=journal,
                account=account,
                credit=amount,
                description="Opening balance"
            )
            
            # Create corresponding asset entry
            asset_account = Account.objects.filter(type='ASSET', is_active=True).first()
            if asset_account:
                JournalLine.objects.create(
                    journal=journal,
                    account=asset_account,
                    debit=amount,
                    description=f"Opening balance for {account.name}"
                )
        
        # Post the journal entry
        post_journal_entry(journal, created_by)
        
        return journal


def fund_petty_cash(fund, amount, created_by):
    """
    Fund a petty cash account
    """
    with transaction.atomic():
        # Create journal entry
        journal = Journal.objects.create(
            date=date.today(),
            description=f"Fund petty cash - {fund.name}",
            source_module='PETTY_CASH',
            created_by=created_by,
            status='POSTED'
        )
        
        # Create journal lines
        JournalLine.objects.create(
            journal=journal,
            account=fund.account,
            debit=amount,
            description=f"Fund {fund.name}"
        )
        
        # Credit bank account (assuming there's a bank account)
        bank_account = Account.objects.filter(
            type='ASSET',
            name__icontains='bank'
        ).first()
        
        if bank_account:
            JournalLine.objects.create(
                journal=journal,
                account=bank_account,
                credit=amount,
                description=f"Transfer to {fund.name}"
            )
        
        # Post the journal entry
        post_journal_entry(journal, created_by)
        
        # Update fund balance
        fund.current_balance += amount
        fund.save()
        
        return journal

