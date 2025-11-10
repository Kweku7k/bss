# Central University ERP - User Manual

**Welcome to Your University ERP System!**

This manual will help you navigate and use the system effectively. Choose your role below to jump to relevant sections.

---

## 📖 Quick Navigation

**Jump to your role:**
- [Staff Users](#for-staff-users) - View profile, apply for leave, submit claims
- [HR Officers](#for-hr-officers) - Manage employees, process payroll
- [Finance Officers](#for-finance-officers) - Journals, accounts, reports
- [Managers/Supervisors](#for-managers) - Approvals, reports

**Common Tasks:**
- [Login & Security](#login--security)
- [Updating Your Profile](#updating-your-profile)
- [Applying for Leave](#applying-for-leave)
- [Submitting Medical Claims](#submitting-medical-claims)
- [Processing Monthly Payroll](#processing-monthly-payroll)
- [Creating Journal Entries](#creating-journal-entries)
- [Running Financial Reports](#running-financial-reports)
- [Troubleshooting](#troubleshooting--faq)

---

## Login & Security

### How to Log In

1. Go to your system URL
2. Enter your **Username** and **Password**
3. If Two-Factor Authentication (2FA) is enabled:
   - Enter the code from your authenticator app
   - Or enter the code sent to your email
4. Click **Login**

### First-Time Login

If this is your first time:
1. Your administrator will provide your username and temporary password
2. Login with these credentials
3. You'll be prompted to **change your password**
4. Set a strong password (minimum 8 characters, mix of letters and numbers)
5. Click **Update Password**

### Forgot Password?

Contact your system administrator or HR department for password reset.

### Two-Factor Authentication (2FA)

For added security, 2FA may be enabled on your account:
- **Authenticator App:** Use Google Authenticator or similar
- **Email:** Code sent to your registered email
- **Backup Codes:** Keep these safe for emergencies

---

## For Staff Users

### Dashboard

When you login, you'll see your dashboard with:
- Your profile summary
- Recent payslips
- Leave balance
- Pending actions
- Quick links to common tasks

### Updating Your Profile

**To view/update your personal information:**

1. Click **Profile** (top right menu, your name)
2. Click **Edit Personal Information**
3. Update fields:
   - Contact information (phone, email)
   - Address
   - Emergency contacts
   - Bank details
4. Click **Submit for Approval**
5. Your changes will be reviewed by HR

**Note:** Some fields (like name, date of birth) can only be changed by HR.

### Applying for Leave

**Step-by-Step:**

1. Go to **Leave** → **Apply for Leave**
2. Select **Leave Type:**
   - Annual Leave
   - Sick Leave
   - Maternity/Paternity Leave
   - Study Leave
   - Other
3. Select **Start Date** and **End Date**
4. System shows **Number of Days**
5. Enter **Reason** for leave
6. Click **Submit Application**

**After Submission:**
- Your supervisor receives notification
- Check **Leave Status** to track approval
- You'll receive notification when approved/rejected

**Checking Leave Balance:**
- Go to **Leave** → **My Leave Balance**
- See available days for each leave type
- View leave history

### Submitting Medical Claims

**For your medical expenses:**

1. Go to **Medical** → **Submit Claim**
2. Fill in details:
   - **Hospital/Clinic** visited
   - **Treatment Date**
   - **Treatment Type** (Outpatient, Inpatient, Dental, etc.)
   - **Patient** (Self, Spouse, Child)
   - **Complaint/Diagnosis**
   - **Amount** paid
3. **Upload Receipt** (required)
4. Click **Submit Claim**

**After Submission:**
- Medical officer reviews claim
- If approved, amount credited to your account
- If excess over entitlement, repayment schedule created

### Viewing Your Payslip

**To see your salary breakdown:**

1. Go to **HR** → **My Payslip**
2. Select **Month** and **Year**
3. Click **View Payslip**
4. Your payslip shows:
   - Basic salary
   - All allowances
   - All deductions
   - Net salary
5. Click **Download PDF** to save a copy

---

## For HR Officers

### Adding a New Employee

**Complete Employee Registration:**

1. Go to **Staff** → **Register New Staff**
2. **Personal Information Tab:**
   - Staff Number (unique)
   - Title, First Name, Surname
   - Date of Birth, Gender
   - Nationality, Marital Status
   - Contact Information
   - National ID/SSNIT Number
3. **Company Information Tab:**
   - Job Title
   - Department/Faculty
   - Contract Type
   - Date of Appointment
   - Basic Salary
   - Bank Details
   - Cost Center
4. Click **Save Employee**

**After Registration, Add:**
- Employee Relations (dependents)
- Education History
- Previous Employment
- Documents (certificates, etc.)

### Processing Monthly Payroll

**Complete Workflow:**

#### Step 1: Generate Payroll
1. Go to **Payroll** → **Process Payroll**
2. Select **Month** and **Year**
3. Click **Process Payroll**
4. System calculates for all staff:
   - Basic salary
   - All allowances (from staff income setup)
   - SSF/PF contributions
   - PAYE (tax)
   - Other deductions (loans, advances, etc.)
   - Net salary

#### Step 2: Review Payroll Register
1. Go to **Payroll** → **Payroll Register**
2. Select same month/year
3. Review all calculations
4. Check for errors
5. Export to Excel if needed for management review

#### Step 3: Approve Payroll
1. On Payroll Register page
2. Review each staff member
3. Toggle **Approval** switch (✓ or ✗)
4. Or use **Approve All** for bulk approval

#### Step 4: Generate Bank Sheet
1. Go to **Payroll** → **Bank Sheet**
2. Select month/year
3. Export to Excel
4. Send to bank for salary transfers

#### Step 5: Generate Payroll Journal (Finance)
1. Go to **Payroll Report** → **Generate Payroll Journal**
2. Select approved month
3. Click **Preview Journal**
4. Verify amounts (Debits should equal Credits)
5. Click **Generate & Post Journal**
6. Journal automatically created in General Ledger

### Managing Staff Income & Deductions

**Setting Up Allowances:**

1. Go to staff profile → **Staff Settings**
2. Click **Create Staff Income**
3. Select **Income Type** (e.g., Housing Allowance)
4. Choose calculation method:
   - **Fixed Amount:** Enter exact amount
   - **Percentage of Basic:** Enter percentage
5. Set **Entitlement** (if less than 100%)
6. Click **Save**

**Setting Up Deductions:**

1. Go to staff profile → **Staff Settings**
2. Click **Create Staff Deduction**
3. Select **Deduction Type**
4. Enter **Amount** or **Percentage**
5. Set if **One-Time** or **Recurring**
6. Click **Save**

### Managing Staff Loans

**Creating a Loan:**

1. Go to staff profile → **Staff Settings**
2. Click **Create Staff Loan**
3. Fill in:
   - **Loan Type** (Staff Loan, Emergency Loan, etc.)
   - **Amount**
   - **Interest** (if applicable)
   - **Start Date** and **End Date**
   - System calculates monthly installment
4. Click **Save**
5. **Activate** loan to start deductions

**Loan appears automatically in payroll deductions.**

### Leave Management

**Approving Leave:**

1. Go to **Leave** → **Pending Approvals**
2. Review application details
3. Click **Approve** or **Reject**
4. Add comments if needed
5. Employee notified automatically

**Checking Leave Balances:**

1. Go to **Leave** → **Leave Balance Report**
2. Select staff member or department
3. View current balances and usage

---

## For Finance Officers

### Creating a Journal Entry

**For Local Currency (GHS) Transactions:**

1. Go to **Ledger** → **Create Journal Entry**
2. Select **Entry Type:** 🏠 **Local Currency**
3. Fill in:
   - **Date** (transaction date)
   - **Cost Center** (department)
   - **Description** (e.g., "Payment for office supplies")
4. **Add Journal Lines:**
   - Click **+ Add Line**
   - Select **Account** from dropdown
   - Enter **Description**
   - Enter amount as **Debit** OR **Credit** (not both!)
   - Repeat for all lines
5. **Check Balance:**
   - Total Debit (red) must equal Total Credit (green)
   - Difference (blue) must show 0.00
6. Click **Save as Draft** or **Post Journal**

**For Foreign Currency Transactions:**

1. Go to **Ledger** → **Create Journal Entry**
2. Select **Entry Type:** 🌍 **Multi-Currency**
3. Fill in header information
4. **IMPORTANT:** Choose ONE currency for ALL lines!
5. **Add Journal Lines:**
   - Select **Account**
   - Select **Currency** (must be SAME for all lines)
   - Exchange rate auto-fills
   - Enter amount (Debit or Credit)
6. System converts to GHS automatically
7. Check balance in both currencies
8. Click **Save** or **Post**

**Example - USD Expense:**
```
Line 1: Office Supplies Expense - Debit $500 USD
Line 2: Bank - USD Account     - Credit $500 USD

System converts: $500 × 12.50 = 6,250 GHS
Result: Balanced in both USD and GHS ✅
```

### Managing Exchange Rates

**Adding Monthly Rates:**

1. Go to **Ledger** → **Exchange Rates** → **Create**
2. Select **From Currency:** USD
3. Select **To Currency:** GHS
4. Enter **Rate:** (e.g., 12.65)
5. Set **Effective Date:** (usually 1st of month)
6. Mark **Active:** ✓
7. Click **Save**

**Best Practice:**
- Add rates at the start of each month
- Use official bank rates
- Keep all historical rates (don't delete)

### Chart of Accounts

**Viewing Accounts:**
1. Go to **Ledger** → **Chart of Accounts**
2. Browse accounts by type
3. Search for specific accounts
4. View account hierarchy

**Adding an Account:**
1. Click **Create Account**
2. Enter:
   - **Code** (unique, e.g., 5015)
   - **Name** (e.g., "Transport Allowance Expense")
   - **Type** (ASSET, LIABILITY, EXPENSE, etc.)
   - **Parent Account** (for hierarchy)
   - **Currency**
3. Click **Save**

**Bulk Upload (CSV):**
1. Click **CSV Upload**
2. Download sample template
3. Fill in your accounts
4. Upload file
5. System creates all accounts at once

### Running Financial Reports

**Trial Balance:**
1. Go to **Ledger** → **Reports** → **Trial Balance**
2. Select **Date Range**
3. Click **Generate**
4. Export to PDF or Excel

**Balance Sheet:**
1. Go to **Ledger** → **Reports** → **Balance Sheet**
2. Select **As of Date**
3. Click **Generate**
4. Shows Assets, Liabilities, and Equity

**Profit & Loss:**
1. Go to **Ledger** → **Reports** → **Profit & Loss**
2. Select **Period** (month/quarter/year)
3. Click **Generate**
4. Shows Income and Expenses

**Ledger Detail Report:**
1. Go to **Ledger** → **Reports** → **Ledger Detail**
2. Select **Account**
3. Select **Date Range**
4. Shows all transactions for that account

### Payroll Journal Generation

**After HR Approves Payroll:**

1. Go to **Payroll Report** → **Generate Payroll Journal**
2. Select **Month** and **Year**
3. Click **Preview Journal**
4. **Review Preview:**
   - Each allowance appears as separate line
   - Each deduction appears as separate line
   - Check Total Debit = Total Credit
5. If balanced, click **Generate & Post Journal**
6. Journal created in General Ledger automatically

**View Generated Journals:**
1. Go to **Payroll Report** → **Payroll Journal History**
2. See all past journals
3. Click **View in Ledger** for details

### Configuring Payroll Account Mappings

**One-Time Setup:**

1. Go to **Payroll Report** → **Account Mapping Setup**
2. For each payroll item, configure:
   - **Account Type** (Basic Salary, Allowance, etc.)
   - **Sub Type** (if applicable, e.g., "Housing Allowance")
   - **Debit Account** (GL account to debit)
   - **Credit Account** (GL account to credit)
   - **Description Template** (use {month} and {year})
3. Click **Save Mapping**

**Required Mappings:**
- Basic Salary
- SSF Employee & Employer
- PF Employee & Employer
- PAYE (Income Tax)
- Net Salary Payable

**Optional Mappings:**
- Each specific allowance type
- Each specific deduction type

---

## For Managers

### Viewing Your Team

1. Go to **Reports** → **Department Report**
2. Select your department
3. View all staff members
4. See their current status

### Approving Leave Requests

1. Check **Notifications** (bell icon)
2. Click on leave application
3. Review details
4. Click **Approve** or **Reject**
5. Add comments if needed

### Viewing Department Reports

1. Go to **Reports**
2. Select report type
3. Filter by your department/cost center
4. Export if needed

---

## Common Tasks - Quick Reference

### How to: Change Your Password

1. Click your name (top right)
2. Click **Change Password**
3. Enter current password
4. Enter new password (twice)
5. Click **Update**

### How to: View Your Salary History

1. Go to **HR** → **Payroll History**
2. Select date range
3. View all past payslips

### How to: Upload Documents

1. Go to your profile
2. Click **Upload Document**
3. Select **Document Type**
4. Choose file
5. Add notes
6. Click **Upload**

### How to: Check Your Leave Balance

1. Go to **Leave** → **My Leave Balance**
2. See available days per leave type
3. View usage history

### How to: Print/Export Reports

Most reports have export options:
- **PDF:** Click "Export to PDF"
- **Excel:** Click "Export to Excel"
- **Print:** Click "Print" or use Ctrl+P

---

## Troubleshooting & FAQ

### Login Issues

**Q: I forgot my password**  
A: Contact your HR department or system administrator for reset.

**Q: 2FA code not working**  
A: Ensure your device time is correct. Try backup code. Contact admin if still failing.

**Q: Account locked**  
A: After 5 failed login attempts, account locks for 30 minutes. Contact admin if urgent.

### Payroll Issues

**Q: My allowance is not showing**  
A: Check with HR that your allowance is set up correctly in Staff Settings.

**Q: Deduction amount seems wrong**  
A: Review your payslip details. Contact HR if calculation seems incorrect.

**Q: Can't see my payslip**  
A: Payslips available only after payroll is processed and approved. Check with HR.

### Leave Issues

**Q: My leave balance is incorrect**  
A: Contact HR to review your leave entitlement and usage.

**Q: Leave application not submitted**  
A: Ensure all required fields are filled. Check for error messages.

**Q: Leave application pending for long time**  
A: Contact your supervisor. They may not have seen the notification.

### Journal Entry Issues

**Q: "Journal not balanced" error**  
A: Total Debits must equal Total Credits. Check all your line amounts.

**Q: "Exchange rate not found"**  
A: Add the exchange rate for that currency and date first (Ledger → Exchange Rates).

**Q: Can't mix currencies in journal**  
A: Correct! All lines must use the SAME currency. See Multi-Currency section above.

**Q: How to correct a posted journal?**  
A: Contact your finance supervisor. Posted journals usually require reversal and new entry.

### General Issues

**Q: Page not loading**  
A: Refresh browser (Ctrl+R). Clear cache if problem persists.

**Q: Changes not saved**  
A: Ensure you clicked "Save" button. Check for error messages in red.

**Q: Can't access certain pages**  
A: You may not have permission for that function. Contact administrator.

---

## Tips for Efficient Use

### Keyboard Shortcuts

- **Ctrl+S:** Save form (where applicable)
- **Esc:** Close modal dialogs
- **Tab:** Move to next field
- **Ctrl+P:** Print current page

### Browser Recommendations

- **Chrome** (recommended)
- **Firefox**
- **Safari**
- **Edge**

**Note:** Internet Explorer not supported.

### Best Practices

1. **Login Daily** - Check for notifications and pending actions
2. **Logout When Done** - Especially on shared computers
3. **Keep Records** - Download important documents (payslips, reports)
4. **Report Issues Promptly** - Contact support if you notice errors
5. **Review Before Submitting** - Double-check all entries before submission

### Data Security

- ✅ Never share your password
- ✅ Logout from shared computers
- ✅ Don't save password on public computers
- ✅ Report suspicious activity
- ✅ Keep your contact info updated

---

## Support Contacts

### Who to Contact:

**Login/Access Issues:**  
→ IT Department: it@central.edu.gh

**HR Issues (Staff, Leave, Payroll):**  
→ HR Department: hr@central.edu.gh

**Finance Issues (Journals, Accounts):**  
→ Finance Department: finance@central.edu.gh

**Medical Claims:**  
→ Medical Officer: medical@central.edu.gh

**General Questions:**  
→ Help Desk: helpdesk@central.edu.gh  
→ Phone: [Your support number]

### Office Hours:
Monday - Friday: 8:00 AM - 5:00 PM  
Saturday: 8:00 AM - 12:00 PM  
Sunday & Public Holidays: Closed

---

## Glossary of Terms

**Base Currency:** Your organization's main currency (GHS)

**Cost Center:** Department or unit for budget tracking

**Debit/Credit:** Accounting entries (Debit = left side, Credit = right side)

**GL (General Ledger):** Central record of all financial transactions

**Journal Entry:** A record of a financial transaction

**Net Salary:** Take-home pay after all deductions

**PAYE:** Pay As You Earn - Income tax

**PF:** Provident Fund (retirement savings)

**SSF:** Social Security Fund

**SSNIT:** Social Security and National Insurance Trust

**2FA:** Two-Factor Authentication (extra security)

---

## Updates & Version History

**Version 1.0 - November 4, 2025**
- Initial user manual release
- Payroll journal generation feature added
- Multi-currency support enhanced
- CSV upload for chart of accounts

---

**Need More Help?**

This manual covers the most common tasks. For detailed technical information, see `SYSTEM_DOCUMENTATION.md`.

For specific questions not covered here, contact your system administrator or help desk.

**Happy Using the System!** 🎉

