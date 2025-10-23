# University ERP — General Ledger Module

## 1. Overview
The **General Ledger (GL)** module serves as the central accounting engine of the university ERP. It records every financial transaction from all subsystems (Fees, Payroll, Procurement, Petty Cash, etc.) into a unified chart of accounts.

Each transaction produces balanced **Debit** and **Credit** entries, ensuring accurate financial records.

---

## 2. Core Components

### A. Chart of Accounts (COA)
Defines all accounts used by the university. Each account has:
- Account Code
- Account Name
- Account Type (Asset, Liability, Income, Expense, Equity)
- Parent Account (for grouping)
- Status (Active/Inactive)

**Example Structure:**

| Code | Account Name | Type | Parent | Description |
|------|---------------|------|---------|--------------|
| 1000 | Assets | Header | - | Root category |
| 1100 | Cash & Bank | Asset | 1000 | - |
| 1110 | Cash at Main Office | Asset | 1100 | Petty cash float |
| 1120 | Bank Account (GCB) | Asset | 1100 | University main account |
| 2000 | Liabilities | Header | - | - |
| 2100 | Student Deposits | Liability | 2000 | Advance payments |
| 3000 | Income | Header | - | - |
| 3100 | Tuition Income | Income | 3000 | - |
| 4000 | Expenses | Header | - | - |
| 4100 | Utilities | Expense | 4000 | Water, electricity |

---

### B. Journal Entries
A journal entry records an accounting event.

**Fields:**
- `date`
- `reference_no` (auto-generated)
- `description`
- `source_module` (e.g., Fees, Payroll, Procurement)
- `created_by`
- `status` (Draft / Posted)

Each journal must have at least 2 lines (Debit & Credit).

**Example:**
> Student pays GH₵1,000  
> Debit: Bank Account GH₵1,000  
> Credit: Tuition Income GH₵1,000  

---

### C. Ledger
The ledger stores cumulative account balances based on journal entries.

Each **Account** has:
- Opening balance  
- Total debits  
- Total credits  
- Closing balance (auto-computed)

**Views:**
- Ledger by account
- Ledger by date range
- Transaction drill-down

---

### D. Petty Cash Management
Manages small cash disbursements and reconciliations.

**Features:**
- Create petty cash funds (linked to Cash account)
- Issue and approve vouchers
- Track balances and top-ups

**Flow:**
1. Admin funds petty cash (GH₵2,000)
2. Officer requests GH₵200 for printing
3. Approve voucher → Dr Printing Expense, Cr Cash
4. Ledger auto-updates

---

### E. Integration Hooks
Other ERP modules will post journal entries here:

| Module | Example Transaction | Ledger Entry |
|---------|---------------------|---------------|
| Fees | Student Payment | Dr Bank, Cr Tuition Income |
| Payroll | Salary Payment | Dr Salary Expense, Cr Bank |
| Procurement | Item Purchase | Dr Supplies Expense, Cr Payables |
| Petty Cash | Refill | Dr Cash, Cr Bank |

---

## 3. Models (Django-Style Example)

```python
class Account(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(choices=ACCOUNT_TYPES, max_length=20)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

class Journal(models.Model):
    reference_no = models.CharField(max_length=20, unique=True)
    date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True)
    source_module = models.CharField(max_length=50)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=[('Draft','Draft'),('Posted','Posted')])

class JournalLine(models.Model):
    journal = models.ForeignKey(Journal, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

class LedgerBalance(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def closing_balance(self):
        if self.account.type in ['Asset', 'Expense']:
            return self.opening_balance + self.total_debit - self.total_credit
        return self.opening_balance - self.total_debit + self.total_credit
```

---

## 4. Core Workflows

### 1. Posting a Transaction
- Receive data (Debit/Credit lines)
- Validate that totals balance
- Create Journal and JournalLines
- Update LedgerBalance for each account

### 2. Petty Cash Workflow
- Create fund → Post opening balance
- Create voucher → Record expense
- Approve → Update ledger
- Request top-up → Transfer Bank → Cash

### 3. Monthly Closing
- Lock transactions for closed months
- Generate trial balance, P&L, balance sheet

---

## 5. Reports

| Report | Description |
|--------|--------------|
| **Trial Balance** | Lists all accounts with total debits/credits for a period |
| **Ledger Detail** | All transactions for a given account |
| **Journal Listing** | All posted journals with filters |
| **Petty Cash Summary** | Funded, spent, and remaining balance |
| **Profit & Loss** | Income vs Expense summary |
| **Balance Sheet** | Assets, Liabilities, and Equity snapshot |

---

## 6. Implementation Roadmap

| Phase | Task | Output | Status |
|-------|------|---------|---------|
| 1 | Setup Chart of Accounts | Basic account structure | [ ] |
| 2 | Journal + Ledger Models | Core accounting engine | [ ] |
| 3 | Posting Logic + Balancing Validation | Accurate double-entry | [ ] |
| 4 | Petty Cash Module | Fund, spend, reconcile | [ ] |
| 5 | Reports (Trial Balance, P&L, Balance Sheet) | Financial reports | [ ] |
| 6 | Integration Hooks | Connect Fees, Payroll, Procurement | [ ] |

