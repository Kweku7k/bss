# General Ledger Module

The General Ledger module is the central accounting engine of the University ERP system. It implements double-entry bookkeeping principles and provides comprehensive financial management capabilities.

## Features

### Core Components

1. **Chart of Accounts**
   - Hierarchical account structure
   - Account types: Asset, Liability, Equity, Income, Expense, Header
   - Account codes and descriptions
   - Parent-child relationships

2. **Journal Entries**
   - Double-entry bookkeeping
   - Automatic reference number generation
   - Source module tracking
   - Draft/Posted status management
   - Balance validation

3. **Ledger Balances**
   - Real-time balance calculation
   - Opening balance tracking
   - Debit/Credit totals
   - Closing balance computation

4. **Petty Cash Management**
   - Fund creation and management
   - Voucher system with approval workflow
   - Balance tracking and reconciliation
   - Automatic journal entry generation

5. **Financial Reports**
   - Trial Balance
   - Balance Sheet
   - Profit & Loss Statement
   - Ledger Detail Reports
   - Journal Listing Reports

## Installation & Setup

### 1. Database Migration

```bash
python manage.py migrate ledger
```

### 2. Set Up Initial Chart of Accounts

```bash
python manage.py setup_chart_of_accounts --admin-username admin
```

This command creates a comprehensive chart of accounts suitable for a university, including:
- Asset accounts (Cash, Bank, Receivables, Fixed Assets)
- Liability accounts (Payables, Deposits, Payroll Liabilities)
- Equity accounts (Retained Earnings, Current Year Surplus)
- Income accounts (Tuition, Fees, Other Income)
- Expense accounts (Personnel, Operating, Academic, Administrative)

### 3. Admin Interface

Access the Django admin interface to manage accounts, journals, and petty cash:
- `/admin/ledger/account/` - Manage chart of accounts
- `/admin/ledger/journal/` - Manage journal entries
- `/admin/ledger/pettycashfund/` - Manage petty cash funds

## Usage Guide

### Creating Journal Entries

1. Navigate to **General Ledger > Journal Entries**
2. Click **New Journal Entry**
3. Fill in the journal header information
4. Add journal lines (minimum 2 lines required)
5. Ensure total debits equal total credits
6. Save as draft or post immediately

### Managing Petty Cash

1. **Create Petty Cash Fund**
   - Go to **General Ledger > Petty Cash**
   - Create a new fund with custodian and maximum amount
   - Fund the account with initial cash

2. **Create Vouchers**
   - Staff can create vouchers for small expenses
   - Specify amount, description, and expense account
   - Submit for approval

3. **Approve and Disburse**
   - Approvers can review and approve vouchers
   - Approved vouchers automatically create journal entries
   - Fund balance is updated automatically

### Generating Reports

1. **Trial Balance**
   - Shows all account balances as of a specific date
   - Validates that debits equal credits
   - Can include or exclude zero-balance accounts

2. **Balance Sheet**
   - Assets, Liabilities, and Equity as of a specific date
   - Shows financial position snapshot

3. **Profit & Loss**
   - Income and expenses for a date range
   - Shows profitability for the period

4. **Ledger Detail**
   - All transactions for a specific account
   - Shows running balance
   - Useful for account analysis

## Integration with Other Modules

The ledger module provides integration hooks for other ERP modules:

### Payroll Integration
```python
from ledger.utils import post_journal_entry
from ledger.models import Journal, JournalLine, Account

# Example: Post salary payment
def post_salary_payment(employee, amount, salary_account, bank_account):
    journal = Journal.objects.create(
        date=date.today(),
        description=f"Salary payment for {employee.get_full_name()}",
        source_module='PAYROLL',
        created_by=request.user,
        status='POSTED'
    )
    
    # Debit salary expense
    JournalLine.objects.create(
        journal=journal,
        account=salary_account,
        debit=amount,
        description=f"Salary for {employee.get_full_name()}"
    )
    
    # Credit bank account
    JournalLine.objects.create(
        journal=journal,
        account=bank_account,
        credit=amount,
        description=f"Salary payment to {employee.get_full_name()}"
    )
    
    post_journal_entry(journal, request.user)
```

### Fees Integration
```python
# Example: Post student fee payment
def post_fee_payment(student, amount, bank_account, tuition_account):
    journal = Journal.objects.create(
        date=date.today(),
        description=f"Fee payment from {student.get_full_name()}",
        source_module='FEES',
        created_by=request.user,
        status='POSTED'
    )
    
    # Debit bank account
    JournalLine.objects.create(
        journal=journal,
        account=bank_account,
        debit=amount,
        description=f"Fee payment from {student.get_full_name()}"
    )
    
    # Credit tuition income
    JournalLine.objects.create(
        journal=journal,
        account=tuition_account,
        credit=amount,
        description=f"Tuition income from {student.get_full_name()}"
    )
    
    post_journal_entry(journal, request.user)
```

## Account Types and Balance Rules

### Asset Accounts
- **Balance Type**: Debit
- **Increase**: Debit
- **Decrease**: Credit
- **Examples**: Cash, Bank, Receivables, Equipment

### Liability Accounts
- **Balance Type**: Credit
- **Increase**: Credit
- **Decrease**: Debit
- **Examples**: Payables, Deposits, Loans

### Equity Accounts
- **Balance Type**: Credit
- **Increase**: Credit
- **Decrease**: Debit
- **Examples**: Retained Earnings, Capital

### Income Accounts
- **Balance Type**: Credit
- **Increase**: Credit
- **Decrease**: Debit
- **Examples**: Tuition Income, Fees

### Expense Accounts
- **Balance Type**: Debit
- **Increase**: Debit
- **Decrease**: Credit
- **Examples**: Salaries, Utilities, Supplies

## Security and Permissions

The ledger module respects Django's permission system. Key permissions:
- `ledger.add_journal` - Create journal entries
- `ledger.change_journal` - Modify journal entries
- `ledger.delete_journal` - Delete journal entries
- `ledger.add_pettycashvoucher` - Create petty cash vouchers
- `ledger.change_pettycashvoucher` - Approve vouchers

## Best Practices

1. **Always validate journal entries** before posting
2. **Use descriptive descriptions** for journal entries
3. **Set up proper account hierarchy** for better reporting
4. **Regular reconciliation** of petty cash funds
5. **Backup financial data** regularly
6. **Use source module tracking** for audit trails
7. **Implement proper approval workflows** for sensitive transactions

## Troubleshooting

### Common Issues

1. **Journal not balanced**
   - Check that total debits equal total credits
   - Verify account selections
   - Review amounts entered

2. **Petty cash fund insufficient**
   - Check current balance
   - Consider adding more funds
   - Review pending vouchers

3. **Report discrepancies**
   - Verify journal posting dates
   - Check account filters
   - Review opening balances

### Support

For technical support or feature requests, contact the development team or create an issue in the project repository.

## Future Enhancements

Planned features for future releases:
- Multi-currency support
- Budget management
- Advanced reporting with charts
- Automated reconciliation
