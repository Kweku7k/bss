# Central University ERP System - Complete Documentation

**Version:** 1.2  
**Last Updated:** November 6, 2025  
**System Type:** University Enterprise Resource Planning (ERP)

**Quick Links:**
- For End Users: See [`USER_MANUAL.md`](USER_MANUAL.md) - User-friendly guide
- For Developers/Admins: This document (technical reference)

---

## 📑 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Modules & Features](#modules--features)
4. [Quick Start Guide](#quick-start-guide)
5. [User Roles & Permissions](#user-roles--permissions)
6. [Detailed Module Documentation](#detailed-module-documentation)
   - 6.1 [Payroll Journal System](#61-payroll-journal-system-latest-feature-)
   - 6.2 [Multi-Currency & Exchange Rates](#62-multi-currency--exchange-rates-)
   - 6.3 [CSV Upload for Chart of Accounts](#63-csv-upload-for-chart-of-accounts)
   - 6.4 [Chart of Accounts Structure](#64-chart-of-accounts-structure)
   - 6.5 [Payroll Account Mapping - Configuration-Based Setup](#65-payroll-account-mapping---configuration-based-setup)
7. [Common Workflows](#common-workflows)
8. [Technical Reference](#technical-reference)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance & Updates](#maintenance--updates)

---

## 1. System Overview

### What is This System?

This is a comprehensive **University ERP System** designed for Central University, Ghana. It manages:
- **Human Resources** (Staff, Payroll, Leave, Benefits)
- **Financial Accounting** (General Ledger, Journals, Accounts)
- **Medical Claims** (Staff & Dependents)
- **Leave Management** (Applications, Approvals, Tracking)
- **Setup & Configuration** (Banks, Schools, Departments, Hospitals)

### Key Characteristics

- **Double-Entry Accounting**: All financial transactions maintain balanced debits and credits
- **Multi-Currency Support**: Handle GHS, USD, and other currencies with automatic conversion
- **Role-Based Access**: Secure permissions for different user types
- **Audit Trail**: Complete history of all transactions and changes
- **Integration**: All modules feed into the General Ledger automatically

---

## 2. Architecture & Technology Stack

### Technology Stack

**Backend:**
- **Django 5.0.3** (Python Web Framework)
- **PostgreSQL** (Database)
- **Python 3.9+**

**Frontend:**
- **Bootstrap 5** (UI Framework)
- **JavaScript** (Interactivity)
- **React** (Optional dashboard - in `frontend/`)

**Security:**
- **Django OTP** (Two-Factor Authentication)
- **Role-Based Access Control** (Custom decorator system)
- **Firebase** (File storage for documents/images)

### Project Structure

```
bss/
├── bss/                    # Main project settings
├── hr/                     # Human Resources module
├── ledger/                 # General Ledger & Accounting
├── setup/                  # System configuration
├── leave/                  # Leave management
├── medical/                # Medical claims
├── templates/              # HTML templates
├── static/                 # CSS, JS, images
├── media/                  # Uploaded files
└── env/                    # Python virtual environment
```

### Database Schema Overview

**Main Apps:**
- `hr`: 40+ models (Employee, Payroll, Loans, etc.)
- `ledger`: 10+ models (Account, Journal, ExchangeRate, etc.)
- `setup`: 20+ models (Bank, School, Department, etc.)
- `leave`: 5+ models (LeaveType, LeaveApplication, etc.)
- `medical`: 5+ models (MedicalEntitlement, MedicalClaim, etc.)

---

## 3. Modules & Features

### 3.1 HR Module (`/hr/`)

**Purpose:** Manage all human resource operations

**Key Features:**

#### Staff Management
- Employee registration with complete personal information
- Staff categories (Academic, Administrative, Senior Staff, etc.)
- Contract tracking and renewal management
- Promotion and transfer history
- Exit management (Resignation, Retirement, Termination)
- Document upload and storage (Firebase integration)
- Staff search and filtering

#### Payroll System
- **Monthly Payroll Processing**
  - Basic salary calculation
  - Allowances (Housing, Transport, Fuel, Responsibility, etc.)
  - Statutory deductions (SSF, PF, PAYE)
  - Other deductions (Loans, Medical, Salary Advance, etc.)
  - Tax reliefs calculation
  - Net salary computation

- **Payroll Reports**
  - Payroll Register
  - Bank Sheet (for bank transfers)
  - Payroll History
  - Allowance Reports
  - Deduction Reports
  - PAYE Reports
  - Statutory Reports (SSF/PF)

- **Payroll Journal Generation** ✨ NEW
  - Automatic journal entry creation from payroll
  - Separate line items for each allowance/deduction
  - Matches hard copy journal format
  - Direct posting to General Ledger
  - Account mapping configuration
  - Balance validation
  - Prevents duplicate journals

#### Compensation & Benefits
- Staff income setup (allowances, benefits)
- Staff deductions setup
- Loan management (application, approval, repayment tracking)
- Medical surcharge tracking
- Tax relief management

#### Leave & Attendance
- Leave balance tracking
- Leave application workflow
- Medical claim tracking

**Main URLs:**
```
/                           # Dashboard
/allstaff                   # View all staff
/newstaff                   # Register new staff
/payroll/processing/        # Process monthly payroll
/payroll/register/          # View payroll register
/payroll/summary/           # Monthly payroll summary ✨ NEW
/payroll/journal/preview/   # Preview payroll journal ✨ NEW
/payroll/journal/history/   # View generated journals ✨ NEW
/payroll/account-mapping/   # Configure GL mappings ✨ NEW
```

---

### 3.2 Ledger Module (`/ledger/`)

**Purpose:** Financial accounting and general ledger management

**Key Features:**

#### Chart of Accounts
- Hierarchical account structure
- Account types: Asset, Liability, Equity, Income, Expense, Header
- Account codes (e.g., 1000, 2100, 5010)
- Active/Inactive status
- CSV import/export

#### Journal Entries
- **Double-Entry Bookkeeping**
  - Every transaction has balanced debits and credits
  - Automatic reference number generation
  - Source module tracking (PAYROLL, FEES, MANUAL, etc.)
  - Draft/Posted status

- **Multi-Currency Support** 💱
  - Transaction currency (GHS, USD, etc.)
  - Base currency (GHS)
  - Automatic currency conversion
  - Exchange rate lookup by date
  - Foreign exchange gain/loss tracking

- **Journal Line Features**
  - Individual line date tracking
  - Account selection from chart
  - Description for each line
  - Debit/Credit amounts
  - Base currency conversion
  - Cost center allocation

- **Smart Exchange Rates** 🎯
  - Date-based rate lookup (uses rate effective on transaction date)
  - Historical rate support
  - Cross-currency conversion
  - Automatic inverse rate calculation

#### Financial Reports
- Trial Balance
- Balance Sheet
- Profit & Loss Statement
- Ledger Detail Reports
- Journal Listing

#### Petty Cash Management
- Petty cash fund creation
- Voucher system with approval workflow
- Balance tracking
- Automatic journal posting

**Main URLs:**
```
/ledger/accounts/           # Chart of accounts
/ledger/journal/create/     # Create journal entry
/ledger/journal/list/       # List all journals
/ledger/journal/<id>/       # View journal details
/ledger/reports/trial-balance/  # Trial balance report
/ledger/petty-cash/         # Petty cash management
```

**Key Models:**
- `Account`: Chart of accounts
- `Journal`: Journal header
- `JournalLine`: Journal detail lines
- `Currency`: Supported currencies
- `ExchangeRate`: Currency conversion rates
- `PettyCashVoucher`: Petty cash transactions

---

### 3.3 Setup Module (`/setup/`)

**Purpose:** System configuration and master data

**Key Features:**
- **Banks & Branches:** Bank information for staff accounts
- **Schools/Faculties:** Academic organizational structure
- **Departments:** Administrative departments
- **Directorates:** University directorates and units
- **Hospitals:** Medical facilities for staff treatment
- **Cost Centers:** Budget allocation tracking
- **Academic Years:** Year management
- **Nationalities, Regions, etc.:** Reference data

**Main URLs:**
```
/setup/banks/               # Manage banks
/setup/schools/             # Manage schools/faculties
/setup/departments/         # Manage departments
/setup/hospitals/           # Manage hospitals
/setup/cost-centers/        # Manage cost centers
```

---

### 3.4 Leave Module (`/leave/`)

**Purpose:** Staff leave management

**Key Features:**
- Leave type configuration (Annual, Sick, Maternity, etc.)
- Leave balance tracking
- Leave application workflow
- Leave approval system
- Leave calendar/history

**Main URLs:**
```
/leave/apply/               # Apply for leave
/leave/approve/             # Approve leave (managers)
/leave/history/             # View leave history
```

---

### 3.5 Medical Module (`/medical/`)

**Purpose:** Medical claim management

**Key Features:**
- Medical entitlement setup
- Medical claim submission
- Treatment type tracking
- Hospital selection
- Surcharge tracking for excess claims
- Automatic repayment schedules

**Main URLs:**
```
/medical/claims/            # Submit medical claims
/medical/entitlements/      # View entitlements
/medical/surcharges/        # Manage surcharges
```

---

## 4. Quick Start Guide

### 4.1 First-Time Setup

#### Step 1: Install Dependencies
```bash
cd /Users/mrsoftlife/Documents/Projects/bss
pip install -r requirement.txt
```

#### Step 2: Run Migrations
```bash
python3 manage.py migrate
```

#### Step 3: Create Superuser
```bash
python3 manage.py createsuperuser
```

#### Step 4: Load Chart of Accounts
```bash
python3 manage.py setup_chart_of_accounts --admin-username <your-username>
```

#### Step 5: Start Server
```bash
python3 manage.py runserver
```

Access at: `http://localhost:8000`

---

### 4.2 Initial Configuration

**In This Order:**

1. **Setup Module:**
   - Add Banks & Branches
   - Add Schools/Faculties
   - Add Departments
   - Add Directorates
   - Add Hospitals
   - Add Cost Centers

2. **HR Module:**
   - Configure Staff Categories
   - Configure Leave Types
   - Configure Income Types (Allowances)
   - Configure Deduction Types

3. **Ledger Module:**
   - Review/Edit Chart of Accounts
   - Set up Currencies
   - Set up Exchange Rates
   - **Configure Payroll Account Mappings** ✨

4. **Medical Module:**
   - Set up Medical Entitlements
   - Configure Treatment Types

---

### 4.3 Monthly Payroll Workflow

**Complete Monthly Process:**

1. **Process Payroll** (`/hr/payroll/processing/`)
   - Select month and year
   - Click "Process Payroll"
   - System calculates all salaries

2. **Review Register** (`/hr/payroll/register/`)
   - Check all calculations
   - Verify amounts
   - Export if needed

3. **Approve Payroll**
   - Toggle approval for each staff member
   - Or bulk approve

4. **View Summary** (`/hr/payroll/summary/`) ✨ NEW
   - See overall monthly totals
   - Export PDF/Excel reports

5. **Generate Payroll Journal** (`/hr/payroll/journal/preview/`) ✨ NEW
   - Select approved month
   - Preview journal entries
   - Verify balanced (Debits = Credits)
   - Click "Generate & Post"
   - Journal automatically posted to ledger!

6. **Generate Bank Sheet** (`/hr/payroll/bank_sheet/`)
   - Export for bank transfer

---

## 5. User Roles & Permissions

### Role Types

#### Superadmin
- Full system access
- User management
- System configuration
- All module access

#### Finance Officer / Finance Admin
- Ledger access
- Journal entry creation
- Financial reports
- Payroll approval
- Payroll journal generation

#### HR Officer / HR Admin
- Staff management
- Payroll processing
- Leave management
- Medical claims

#### Department Head / Manager
- View departmental staff
- Leave approval
- Reports

#### Staff (Regular Users)
- View own profile
- Update personal info
- Apply for leave
- Submit medical claims
- View own payroll

### Permission Tags

Custom permission system using `@tag_required()` decorator:
- `view_payroll`
- `process_payroll`
- `approve_payroll`
- `view_loan_history`
- `create_journal`
- `view_financial_reports`
- etc.

---

## 6. Detailed Module Documentation

### 6.1 Payroll Journal System (Latest Feature) ✨

#### Overview
Automatically generates accounting journal entries from approved payroll data and posts them to the General Ledger.

#### How It Works

**Step 1: Configure Account Mappings (One-Time)**

Go to `/hr/payroll/account-mapping/` and map payroll items to GL accounts:

| Payroll Item | Debit Account | Credit Account | Description Template |
|-------------|---------------|----------------|---------------------|
| Basic Salary | 5010 - Salaries Expense | (same) | Consolidated Basic Salary - {month} {year} |
| Housing Allowance | 5011 - Housing Expense | (same) | Housing Allowance |
| SSF Employer | 5020 - SSF Employer | 2110 - SSF Payable | S.S.F Employer - {month} {year} |
| PF Employer | 5030 - PF Employer | 2120 - PF Payable | Provident Fund-Employer |
| PAYE | (n/a) | 2130 - PAYE Payable | Income Tax |
| Net Salary | (n/a) | 2140 - Salaries Payable | Total Net Salary (Bank/Cash) |

**Note:** You can map specific allowances (Transport, Fuel, etc.) or use a generic allowance mapping.

**Step 2: Generate Journal After Payroll Approval**

1. Process and approve monthly payroll
2. Go to `/hr/payroll/journal/preview/`
3. Select month and year
4. Click "Preview Journal"
5. Review all entries (each allowance/deduction is a separate line)
6. Verify **Debits = Credits** (must balance!)
7. Click "Generate & Post Journal"

**Journal Format (Matches Hard Copy):**

```
CONSOLIDATED PAYROLL JOURNAL FOR November, 2024

Line #  Description                      Debit (GH₵)    Credit (GH₵)
1       Consolidated Basic Salary        1,319,192.37   0.00
2       Fuel Benefits                    93,028.01      0.00
3       Transport Reimbursement          143,793.21     0.00
4       Responsibility (25%)             5,341.50       0.00
...
20      Provident Fund-Employer          1,794,600.75   0.00
21      S.S.F (13%)                      0.00           138,388.74
22      Income Tax                       0.00           49,424.00
23      CULEA DUES                       0.00           15,500.00
24      CUSCU Monthly contributions      0.00           5,411.97
...
40      Total Net Salary (Bank/Cash)     0.00           1,794,600.75

Grand Total:                             2,725,145.63   2,725,145.63 ✅
```

**Key Features:**
- ✅ Separate line for each allowance/deduction type
- ✅ Line numbering (matching your hard copy)
- ✅ Automatic balance validation
- ✅ Prevents duplicate generation
- ✅ Links to General Ledger
- ✅ Full audit trail

**View History:**
- Go to `/hr/payroll/journal/history/`
- See all generated journals
- Click "View in Ledger" to see full entry

---

### 6.2 Multi-Currency & Exchange Rates 💱

#### How Exchange Rates Work

**Smart Date-Based Lookup:**

The system automatically finds the exchange rate that was **effective on the transaction date**.

**Example:**

Your Exchange Rates:
```
USD → GHS
├─ Jan 1, 2025:  Rate = 12.00
├─ Feb 1, 2025:  Rate = 12.30
├─ Mar 1, 2025:  Rate = 12.50
└─ Nov 3, 2025:  Rate = 12.65 (current)
```

Journal Lines:
```
Line dated Feb 15, 2025:  Uses rate 12.30 ✅ (from Feb 1)
Line dated Nov 4, 2025:   Uses rate 12.65 ✅ (from Nov 3)
```

**The Smart Lookup Algorithm:**

When you create a journal line with a date and currency:
1. **Looks for the rate** effective on or before the journal line date
2. **Picks the most recent** rate before that date
3. **Uses historical rates** for backdated entries
4. **Uses current rates** for today's entries

**Setting Up Exchange Rates:**

1. Go to `/ledger/exchange-rates/`
2. Select currencies (From: USD, To: GHS)
3. Enter rate (e.g., 12.65)
4. Set effective date (e.g., Nov 3, 2025)
5. Mark as Active
6. Save

**The system will:**
- Use this rate for all transactions dated Nov 3, 2025 onwards
- Use previous rates for historical dates
- Automatically calculate inverse rates (GHS → USD)
- Support cross-currency conversions
- Keep historical rates for audit trail

#### Best Practices for Exchange Rates

**Monthly Rate Updates (Recommended):**
```
1st of every month:
  1. Check central bank rates
  2. Go to Ledger → Exchange Rates → Create
  3. Add new rates for each currency
  4. Set Effective Date = 1st of month
  5. Mark as Active
```

**Keep All Historical Rates:**
- ✅ Never delete old rates
- ✅ Backdated entries need them
- ✅ Audit trail requires them
- ✅ Financial reports need accurate history

**Multiple Rates Per Day:**
If rate changes during the day, system uses most recent for that date.

#### Multi-Currency Journal Entries

**IMPORTANT RULE:** All lines in a journal must use the SAME currency!

**✅ CORRECT Example:**
```
Journal Entry: USD Expense Payment
Currency: USD (for ALL lines)

Line 1: Office Supplies Expense
  Debit: $500.00 USD
  Rate: 12.50 (auto-filled)
  
Line 2: Bank - USD Account
  Credit: $500.00 USD
  Rate: 12.50 (auto-filled)

Result in Base Currency (GHS):
  Debit: 6,250.00 GHS
  Credit: 6,250.00 GHS
  ✅ Balanced!
```

**❌ WRONG Example:**
```
Line 1: Expense $400 USD
Line 2: Bank 5,060 GHS
❌ Won't balance! Different currencies!
```

**Two Entry Types:**
1. **Local Currency (GHS)** - For most transactions
   - Currency and Rate columns hidden
   - Simple entry
   - 99% of daily transactions

2. **Multi-Currency** - For foreign currency
   - Currency and Rate columns visible
   - ALL lines must use SAME currency
   - System converts to GHS automatically

---

### 6.3 CSV Upload for Chart of Accounts

#### Overview
Bulk upload your chart of accounts using CSV files - much faster than one-by-one entry.

#### How to Upload

1. **Go to:** Ledger → Chart of Accounts
2. **Click:** "CSV Upload" button (top right)
3. **Select:** Your prepared CSV file
4. **Click:** "Upload and Import"

#### CSV File Format

**Required Columns:**
| Column | Description | Example |
|--------|-------------|---------|
| Code | 4-10 digit account code (unique) | 1000, 1100, 1110 |
| Name | Account name | Assets, Cash, Bank |
| Type | Account type | ASSET, LIABILITY, EXPENSE |
| Currency | Currency code | GHS, USD, EUR |

**Optional Columns:**
| Column | Description | Example |
|--------|-------------|---------|
| Parent Code | Parent account code | 1000 (for account 1100) |
| Description | Additional details | Main office petty cash |

**Valid Account Types:**
- ASSET, LIABILITY, EQUITY, INCOME, EXPENSE, HEADER

#### Sample CSV Content
```csv
Code,Name,Type,Parent Code,Currency,Description
1000,Assets,HEADER,,GHS,Root asset category
1100,Current Assets,HEADER,1000,GHS,Short-term assets
1110,Cash at Office,ASSET,1100,GHS,Main office petty cash
1120,Bank Account,ASSET,1100,GHS,Main bank account
2000,Liabilities,HEADER,,GHS,Root liability category
2100,Accounts Payable,LIABILITY,2000,GHS,Vendor payables
```

#### Important Rules

1. **Create Parent Accounts First**
   - Order CSV so parent accounts appear before child accounts
   - Example: 1000 → 1100 → 1110

2. **Currency Must Exist**
   - Add currencies first at Ledger → Currencies

3. **Update Behavior**
   - Existing accounts (same code) will be UPDATED
   - Can upload same file multiple times

4. **File Requirements**
   - UTF-8 encoding
   - Maximum 5MB
   - .csv extension

#### Troubleshooting

**"Missing required columns"**
→ Ensure CSV has: Code, Name, Type, Currency

**"Currency 'XXX' not found"**
→ Add currency in Ledger → Currencies first

**"Parent account not found"**
→ Ensure parent account exists or comes earlier in CSV

**"Invalid account type"**
→ Use valid types: ASSET, LIABILITY, EQUITY, INCOME, EXPENSE, HEADER

### 6.4 Chart of Accounts Structure

**Standard University Account Structure:**

```
1000 - ASSETS
  1100 - Current Assets
    1110 - Cash at Main Office
    1120 - Bank Account (GCB)
    1130 - Accounts Receivable
  1200 - Fixed Assets
    1210 - Buildings
    1220 - Equipment
    1230 - Furniture & Fixtures

2000 - LIABILITIES
  2100 - Current Liabilities
    2110 - SSF Payable
    2120 - PF Payable
    2130 - PAYE Payable
    2140 - Salaries Payable
    2150 - Student Deposits

3000 - EQUITY
  3100 - Retained Earnings
  3200 - Current Year Surplus

4000 - INCOME
  4100 - Tuition Income
  4200 - Fees Income
  4300 - Other Income

5000 - EXPENSES
  5010 - Salaries Expense
  5011 - Housing Allowance Expense
  5020 - SSF Employer Expense
  5030 - PF Employer Expense
  5100 - Utilities Expense
  5200 - Supplies Expense
```

**Account Types:**
- **ASSET**: What you own (Cash, Bank, Equipment)
- **LIABILITY**: What you owe (Payables, Loans)
- **EQUITY**: Net worth (Retained Earnings)
- **INCOME**: Revenue (Tuition, Fees)
- **EXPENSE**: Costs (Salaries, Utilities)
- **HEADER**: Category groupings (no transactions)

---

### 6.5 Payroll Account Mapping - Configuration-Based Setup

#### Overview

The Payroll Account Mapping system allows you to map payroll components (allowances, deductions, loans, medical surcharges) to GL accounts. This ensures proper journal entries when generating payroll journals.

**Key Feature:** All mappings are based on **CONFIGURATION TABLES** (setup), not on actual staff assignments. This allows you to set up account mappings BEFORE assigning them to any staff.

#### What Gets Mapped

1. **Allowances** → From `IncomeType` (Setup → Income Type)
2. **Deductions** → From `DeductionType` (Setup → Deduction Type)
3. **Loans** → From `ChoicesLoanType` (HR → Choices Loan Type)
4. **Medical Surcharges** → From `ChoicesMedicalTreatment` (HR → Choices Medical Treatment)
5. **Withholding Taxes** → System-calculated (`Withholding Tax`, `WHT - Rent`) with dedicated account types

#### How It Works

**Configuration Flow:**
```
1. Admin adds type to configuration table
   ↓
2. Type appears in Payroll Account Mapping page
   ↓
3. Finance Officer maps type to GL account
   ↓
4. HR assigns type to staff
   ↓
5. Payroll generates with deductions
   ↓
6. Journal entries use mapped accounts
```

#### Setting Up Mappings

**Step 1: Add Configuration Types**

```
Allowances:
- Django Admin → Setup → Income Type → Add
- Example: "Housing Allowance", "Transport"

Deductions:
- Django Admin → Setup → Deduction Type → Add
- Example: "Union Dues", "Staff Welfare"

Loans:
- Django Admin → HR → Choices Loan Type → Add
- Example: "CUSSC", "Ecobank", "Bank Loan"

Medical Treatments:
- Django Admin → HR → Choices Medical Treatment → Add
- Example: "OPD", "Glasses", "Dental", "Maternity"
```

**Step 2: Map to GL Accounts**

1. Go to `/hr/payroll-account-mapping/`
2. View "Available Allowances" and "Available Deductions" lists
3. For each type, create a mapping:
   - **Account Type**: Select "Allowance" or "Other Deductions"
   - **Sub Type**: Enter EXACT name from configuration table (use autocomplete)
   - **Debit Account**: For allowances (expense account)
   - **Credit Account**: For deductions (liability/payable account)
   - **Description**: Journal line description template

**Example Mappings:**

| Type | Sub Type | Account Type | Debit | Credit | Description |
|------|----------|--------------|-------|--------|-------------|
| Allowance | Housing Allowance | allowance | 5011 | - | Housing Allowance Expense |
| Deduction | Union Dues | other_deduction | - | 2160 | Union Dues Payable |
| Loan | CUSSC | other_deduction | - | 20028 | CUSSC Loan Payable |
| Loan | Ecobank | other_deduction | - | 20025 | Ecobank Payable |
| Medical | Medical Surcharge OPD | other_deduction | - | 50017 | Medical Expenses - OPD |
| Medical | Medical Surcharge Glasses | other_deduction | - | 50017 | Medical Expenses - Glasses |
| Statutory | — | wht_general | - | 20008 | Withholding Tax (Non-Rent) |
| Statutory | — | wht_rent | - | 20008 | Withholding Tax - Rent |

#### Automated Deductions

**Loans:**
- When a staff loan is **active** and within payroll month
- System automatically adds loan installment as deduction
- Deduction name = loan type (e.g., "CUSSC", "Ecobank")
- Uses mapped account in journal

**Medical Surcharges:**
- When staff exceeds medical entitlement
- System creates `MedicalSurcharge` record
- When surcharge is **active**, monthly installment deducted automatically
- Deduction name = "Medical Surcharge {treatment}" (e.g., "Medical Surcharge OPD")
- Uses mapped account in journal

#### Viewing Mappings

The mapping page shows all configured types with status badges:

```
Available Allowances:
├── Housing Allowance          ✅ Mapped
├── Transport                  ✅ Mapped
└── Fuel                       (unmapped)

Available Deductions:
├── Union Dues                 ✅ Mapped
├── Staff Welfare              ✅ Mapped
├── CUSSC                 🔵 Loan ✅ Mapped
├── Ecobank               🔵 Loan ✅ Mapped
├── Medical Surcharge OPD ⚫ Medical ✅ Mapped
└── Medical Surcharge Glasses ⚫ Medical ✅ Mapped
```

**Badges:**
- ✅ Green = Mapped to account
- 🔵 Blue = Loan type
- ⚫ Gray = Medical surcharge

#### Journal Entry Generation

When generating payroll journal:

1. System collects all deductions from all staff for the month
2. Groups by deduction type (e.g., all "CUSSC" loans together)
3. Looks up `PayrollAccountMapping` for each type
4. Creates journal line with mapped account
5. If no mapping found, uses generic "Other Deductions" mapping (if exists)

**Example Journal Entry:**

```
PAYROLL-SEPTEMBER-2025                        Date: 2025-09-30

DEBIT:  Basic Salary Expense        100,000.00
DEBIT:  Housing Allowance Expense    20,000.00
DEBIT:  Transport Expense            10,000.00

CREDIT: SSF Payable (13%)            13,000.00
CREDIT: Income Tax Payable            8,500.00
CREDIT: CUSSC Loan Payable            2,500.00  ← Mapped from loan type
CREDIT: Ecobank Loan Payable          1,800.00  ← Mapped from loan type
CREDIT: Medical Expenses - OPD          183.33  ← Mapped from surcharge
CREDIT: Union Dues Payable              500.00
CREDIT: Net Salary Payable          103,516.67
                                   ───────────
TOTAL:                             130,000.00  130,000.00 ✓
```

#### Troubleshooting

**Issue: New deduction type not showing**
- **Cause**: Not added to configuration table
- **Fix**: Add to appropriate configuration table (DeductionType, ChoicesLoanType, etc.)

**Issue: Deduction in payroll but not in journal**
- **Cause**: No account mapping exists
- **Fix**: Create mapping in Payroll Account Mapping page

**Issue: Wrong account used in journal**
- **Cause**: Sub type name mismatch (case-sensitive)
- **Fix**: Ensure sub_type in mapping EXACTLY matches name in configuration table

**Issue: Duplicate entries in Available list**
- **Cause**: System bug (shouldn't happen with current code)
- **Fix**: Deduplication logic prevents this - contact support

#### Best Practices

1. **Setup order**: Configuration → Mapping → Assignment
2. **Naming consistency**: Use exact names from configuration tables
3. **Regular review**: Monthly review available types for unmapped items
4. **Chart of accounts**: Ensure accounts exist before mapping
5. **Test first**: Create test mappings with small amounts before full rollout

#### Database Models

**Configuration Models:**
```python
IncomeType (setup.models)
├── name: CharField
├── taxable: Boolean
└── withholding_tax: Boolean

DeductionType (setup.models)
└── name: CharField

ChoicesLoanType (hr.models)
└── name: CharField

ChoicesMedicalTreatment (hr.models)
└── name: CharField
```

**Mapping Model:**
```python
PayrollAccountMapping (hr.models)
├── account_type: 'allowance' or 'other_deduction'
├── sub_type: CharField (references config table name)
├── debit_account: FK to Account (for allowances)
├── credit_account: FK to Account (for deductions)
└── description_template: CharField
```

#### Quick Reference

**URLs:**
- Mapping setup: `/hr/payroll-account-mapping/`
- Preview journal: `/hr/preview-payroll-journal/`
- Generate journal: `/hr/generate-payroll-journal/`

**Configuration Paths:**
- Income types: Django Admin → Setup → Income Type
- Deduction types: Django Admin → Setup → Deduction Type
- Loan types: Django Admin → HR → Choices Loan Type
- Medical treatments: Django Admin → HR → Choices Medical Treatment

---

## 7. Common Workflows

### 7.1 Adding a New Employee

1. Go to `/newstaff`
2. Fill Personal Information tab
3. Fill Company Information tab (job, salary, bank)
4. Save employee
5. Add additional info:
   - Employee Relations (dependents)
   - Education history
   - Previous work experience
   - Staff bank details

### 7.2 Processing Monthly Payroll

See section 4.3 above for complete workflow.

### 7.3 Creating a Manual Journal Entry

1. Go to `/ledger/journal/create/`
2. Select date and currency
3. Enter description
4. Add lines:
   - Select account
   - Enter amount as Debit OR Credit
   - Add description
   - Set line date (defaults to journal date)
5. Verify: **Total Debits = Total Credits**
6. Save as Draft or Post immediately
7. If foreign currency, review converted amounts

### 7.4 Running Financial Reports

1. Go to `/ledger/reports/trial-balance/`
2. Select date range
3. Click "Generate Report"
4. Export to PDF/Excel if needed

### 7.5 Managing Staff Loans

1. Go to staff profile → `/hr/payroll/<staffno>`
2. Click "Create Staff Loan"
3. Enter:
   - Loan type
   - Amount
   - Interest
   - Start/End dates
4. System calculates monthly installment
5. Activate loan
6. Loan deductions appear automatically in payroll

---

## 8. Technical Reference

### 8.1 Key Models

#### HR Module

**Employee**
```python
- staffno (PK)
- fname, lname, middlenames
- dob, gender, nationality
- email_address, active_phone
- ssnitno, tin
- staff_pix (Firebase URL)
```

**Payroll**
```python
- staffno (FK to Employee)
- month (DateField)
- basic_salary, total_income, gross_salary
- income_tax, ssf_employee, ssf_employer
- pf_employee, pf_employer
- total_deduction, net_salary
- is_approved, is_journalized ✨ NEW
- payroll_journal (FK) ✨ NEW
```

**PayrollAccountMapping** ✨ NEW
```python
- account_type (basic_salary, allowance, etc.)
- sub_type (e.g., "Housing Allowance")
- debit_account (FK to Account)
- credit_account (FK to Account)
- description_template
- is_active
```

**PayrollJournal** ✨ NEW
```python
- month (DateField)
- journal (FK to Journal)
- reference (e.g., "PAYROLL-JAN-2025")
- total_debit, total_credit
- staff_count
- is_posted
- created_by, created_at
```

#### Ledger Module

**Account**
```python
- code (unique)
- name
- account_type (ASSET, LIABILITY, etc.)
- parent (FK to self)
- is_active
```

**Journal**
```python
- reference (auto-generated)
- date
- description
- source_module (PAYROLL, FEES, MANUAL, etc.)
- status (DRAFT, POSTED)
- created_by
```

**JournalLine**
```python
- journal (FK to Journal)
- line_number
- account (FK to Account)
- description
- debit, credit (base currency)
- currency, exchange_rate
- foreign_debit, foreign_credit
- date (line-specific date) ✨
```

**Currency**
```python
- code (USD, GHS, EUR)
- name, symbol
- is_base_currency
- decimal_places
```

**ExchangeRate**
```python
- from_currency, to_currency (FK to Currency)
- rate
- effective_date (date rate becomes active)
- is_active
```

---

### 8.2 Important Functions

#### Exchange Rate Lookup
```python
ExchangeRate.get_rate(from_currency, to_currency, as_of_date)
```
Returns the appropriate exchange rate for a given date.

#### Payroll Calculator
```python
# In hr/payroll_helper.py
PayrollCalculator.calculate_payroll(employee, month)
```
Calculates all payroll components for an employee.

#### Journal Balance Check
```python
journal.is_balanced()
```
Verifies that total debits equal total credits.

---

### 8.3 URL Patterns Summary

**HR Module:**
```
/                                       # Dashboard
/allstaff                               # Staff list
/newstaff                               # New staff
/staff_details/<staffno>                # Staff details
/payroll/processing/                    # Process payroll
/payroll/register/                      # Payroll register
/payroll/summary/                       # Payroll summary ✨
/payroll/journal/preview/               # Journal preview ✨
/payroll/journal/generate/              # Generate journal ✨
/payroll/journal/history/               # Journal history ✨
/payroll/account-mapping/               # Account mappings ✨
```

**Ledger Module:**
```
/ledger/accounts/                       # Chart of accounts
/ledger/journal/create/                 # Create journal
/ledger/journal/list/                   # Journal list
/ledger/journal/<id>/                   # Journal detail
/ledger/reports/trial-balance/          # Trial balance
/ledger/exchange-rates/                 # Exchange rates
```

---

### 8.4 Security Decorators

**@login_required**
```python
@login_required
def my_view(request):
    # User must be logged in
```

**@role_required**
```python
@role_required(['superadmin', 'finance officer'])
def my_view(request):
    # User must have one of these roles
```

**@tag_required**
```python
@tag_required('process_payroll')
def my_view(request):
    # User must have this permission tag
```

---

## 9. Troubleshooting

### Common Issues

#### Issue: "No approved payrolls found"
**Solution:** Make sure you've processed and approved payroll for that month first.

#### Issue: "Missing account mappings"
**Solution:** Go to `/hr/payroll/account-mapping/` and configure all required mappings.

#### Issue: "Journal not balanced"
**Solution:** 
- Check payroll calculations
- Verify all allowances/deductions have account mappings
- Contact administrator if issue persists

#### Issue: "Exchange rate not found"
**Solution:** Go to `/ledger/exchange-rates/` and add a rate for the currency and date.

#### Issue: "Cannot generate duplicate journal"
**Solution:** A journal already exists for that month. View it in Journal History. If you need to regenerate, delete/reverse the existing one first.

#### Issue: Database connection error
**Solution:** 
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check database settings in bss/settings.py
```

---

## 10. Maintenance & Updates

### Regular Maintenance Tasks

#### Daily
- Monitor system logs (`/hr/logs/`)
- Check failed transactions
- Backup database

#### Monthly
- Generate and post payroll journals
- Review financial reports
- Archive old data if needed
- Update exchange rates

#### Quarterly
- Review user permissions
- Update system documentation
- Check for Django security updates

### Database Backup

```bash
# Backup
pg_dump central_university > backup_$(date +%Y%m%d).sql

# Restore
psql central_university < backup_20250104.sql
```

### Updating the System

```bash
# 1. Backup database first!

# 2. Pull latest code
git pull origin main

# 3. Install new dependencies
pip install -r requirement.txt

# 4. Run migrations
python3 manage.py migrate

# 5. Collect static files
python3 manage.py collectstatic --noinput

# 6. Restart server
sudo systemctl restart gunicorn  # or your process manager
```

---

## Appendix: Feature Change Log

### November 6, 2025 - Configuration-Based Payroll Account Mapping
- ✅ **Major Fix**: Payroll Account Mapping now uses CONFIGURATION TABLES instead of staff assignments
- ✅ Allowances pulled from `IncomeType` (Setup → Income Type)
- ✅ Deductions pulled from `DeductionType` (Setup → Deduction Type)
- ✅ Loans pulled from `ChoicesLoanType` (HR → Choices Loan Type)
- ✅ Medical surcharges pulled from `ChoicesMedicalTreatment` (HR → Choices Medical Treatment)
- ✅ Enables proactive account mapping BEFORE assigning to staff
- ✅ Fixed duplicate entries in available deductions list
- ✅ Added visual badges (Loan 🔵, Medical ⚫, Statutory 🟡) to distinguish deduction types
- ✅ Added dedicated account types for Withholding Tax (`wht_general`) and WHT - Rent (`wht_rent`)
- ✅ Added comprehensive documentation to section 6.5
- ✅ Updated templates to show deduction categories
- ✅ Improved user experience with autocomplete for configuration names

### November 4, 2025 - Documentation Consolidation & Payroll Journal System
- ✅ Consolidated all documentation into single SYSTEM_DOCUMENTATION.md file
- ✅ Created USER_MANUAL.md for end-users (accessible from app settings)
- ✅ Added CSV Upload guide to main documentation
- ✅ Added Multi-Currency & Exchange Rate details
- ✅ Improved payroll journal documentation with hard copy format
- ✅ Added PayrollAccountMapping model
- ✅ Added PayrollJournal model
- ✅ Added is_journalized flag to Payroll
- ✅ Created payroll summary view with PDF/Excel export
- ✅ Created account mapping configuration
- ✅ Created journal preview and generation
- ✅ Created journal history view
- ✅ Updated journal format to match hard copy (separate lines for each item)
- ✅ Added line numbering to journals
- ✅ Support for individual allowance/deduction mapping

### Previous Updates
- Multi-currency support with smart date-based exchange rates
- Line-specific dates in journal entries
- Petty cash management
- Medical surcharge tracking
- Loan management system
- CSV import/export for chart of accounts
- Role-based access control
- Two-factor authentication
- Journal editing capability

---

## Contact & Support

**System Administrator:** [Your contact info]  
**Technical Support:** [Support email/phone]  
**Documentation:** This file (SYSTEM_DOCUMENTATION.md)

---

## Quick Reference Card

### Most Used URLs
```
Dashboard:           /
Staff List:          /allstaff
New Staff:           /newstaff
Process Payroll:     /hr/payroll/processing/
Payroll Summary:     /hr/payroll/summary/
Generate Journal:    /hr/payroll/journal/preview/
Create Journal:      /ledger/journal/create/
Chart of Accounts:   /ledger/accounts/
Trial Balance:       /ledger/reports/trial-balance/
Account Mappings:    /hr/payroll/account-mapping/
```

### Key Keyboard Shortcuts
- **Ctrl+S**: Save form (where applicable)
- **Esc**: Close modal dialogs
- **Tab**: Navigate form fields

### Support Contacts
- HR Issues: hr@central.edu.gh
- Finance Issues: finance@central.edu.gh
- Technical Issues: it@central.edu.gh

---

**End of Documentation**

*This is a living document. Update it whenever you make system changes!*





######## This is for Permission Tags ########
from hr.models import PermissionTag  # adjust if needed

TAGS = {
    "Payroll": [
        "staff_income_upload",
    ],
}

for category, tag_list in TAGS.items():
    for tag in tag_list:
        PermissionTag.objects.get_or_create(
            name=tag,
            category=category,
        )