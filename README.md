# Central University ERP System

**A comprehensive Enterprise Resource Planning system for university management**

![Version](https://img.shields.io/badge/version-1.1-blue)
![Django](https://img.shields.io/badge/Django-5.0.3-green)
![Python](https://img.shields.io/badge/Python-3.9+-yellow)

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirement.txt

# 2. Run migrations
python3 manage.py migrate

# 3. Create superuser
python3 manage.py createsuperuser

# 4. Start server
python3 manage.py runserver
```

Access at: `http://localhost:8000`

---

## 📚 Documentation

**Start Here:**
- 👤 **[USER_MANUAL.md](USER_MANUAL.md)** - For all users (staff, HR, finance)
- 🔧 **[SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md)** - For admins and developers
- 📑 **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Quick navigation guide

**Access Help in App:**
- Click **"User Manual"** in the sidebar
- Or go to: `/help/manual/`

---

## 🎯 What This System Does

### HR Management
- Employee registration and management
- Complete payroll processing
- Loan management
- Leave tracking
- Medical claims
- Staff documents

### Financial Accounting
- General Ledger
- Double-entry bookkeeping
- Multi-currency support
- Journal entries
- Financial reports
- Petty cash management
- **Automated payroll journal generation** ✨ NEW

### System Configuration
- Banks, branches, departments
- Schools, faculties, directorates
- Hospitals and medical facilities
- Chart of accounts
- Exchange rates
- User roles and permissions

---

## ✨ Latest Features (November 2025)

### Payroll Journal System
- Automatic journal generation from approved payroll
- Separate line items for each allowance/deduction
- Account mapping configuration
- Preview before posting
- Balance validation
- Direct posting to General Ledger
- Complete audit trail

**Benefits:**
- ✅ Saves hours of manual journal entry
- ✅ Eliminates calculation errors
- ✅ Ensures proper accounting
- ✅ Links payroll to ledger automatically

---

## 📱 Key Modules

### 1. HR (`/hr/`)
- Staff Management
- Payroll Processing
- Loan Management
- Leave Tracking
- Reports & Analytics

### 2. Ledger (`/ledger/`)
- Chart of Accounts
- Journal Entries
- Multi-Currency
- Financial Reports
- Petty Cash

### 3. Setup (`/setup/`)
- Banks & Branches
- Schools & Departments
- Hospitals
- System Configuration

### 4. Leave (`/leave/`)
- Leave Applications
- Leave Approvals
- Leave Balance

### 5. Medical (`/medical/`)
- Medical Claims
- Entitlements
- Surcharge Tracking

---

## 🛠️ Technology Stack

- **Framework:** Django 5.0.3
- **Database:** PostgreSQL
- **Frontend:** Bootstrap 5, JavaScript
- **Security:** Django OTP (2FA), Role-based access
- **File Storage:** Firebase
- **Reports:** PDF, Excel export

---

## 👥 User Roles

- **Superadmin** - Full system access
- **Finance Officer** - Ledger, journals, reports
- **HR Officer** - Staff, payroll, leave
- **Department Head** - Team management, approvals
- **Staff** - Personal profile, leave, claims

---

## 🔐 Security Features

- Two-Factor Authentication (2FA)
- Role-Based Access Control
- Permission Tags
- Session Management
- Audit Logging
- Secure Password Requirements

---

## 📊 Key Features

### Payroll
- Automated calculations
- Multiple income types
- Multiple deduction types
- Tax calculations (PAYE)
- Statutory deductions (SSF, PF)
- Loan deductions
- Medical surcharge
- **Automated journal generation** ✨

### Accounting
- Double-entry bookkeeping
- Multi-currency support
- Smart exchange rates (date-based)
- Trial balance
- Balance sheet
- Profit & loss
- Ledger reports

### Data Management
- CSV bulk upload
- PDF/Excel export
- Data validation
- Error handling

---

## 📖 Common Workflows

### Processing Monthly Payroll
1. Generate payroll
2. Review register
3. Approve payroll
4. Generate bank sheet
5. **Generate payroll journal** ✨
6. Distribute payslips

### Creating Journal Entry
1. Select entry type (local/multi-currency)
2. Enter transaction details
3. Add journal lines
4. Verify balance
5. Post journal

### Managing Staff
1. Register employee
2. Set up company info
3. Configure income/deductions
4. Process monthly payroll
5. Track history

---

## 🆘 Getting Help

**Documentation:**
- In-app manual: Click "User Manual" in sidebar
- Files: See documentation files listed above

**Support:**
- IT Support: it@central.edu.gh
- HR Support: hr@central.edu.gh
- Finance Support: finance@central.edu.gh

**Office Hours:**
Monday - Friday: 8:00 AM - 5:00 PM

---

## 🔄 System Requirements

**Server:**
- Ubuntu 20.04+ or similar Linux
- Python 3.9+
- PostgreSQL 12+
- 4GB RAM minimum
- 20GB disk space

**Client (Browser):**
- Chrome (recommended)
- Firefox
- Safari
- Edge

---

## 📝 License & Credits

**Developed For:** Central University, Ghana  
**System Type:** Custom ERP Solution  
**Status:** Production Ready ✅

---

## 🎉 Recent Updates

**November 4, 2025:**
- ✅ Payroll journal system implemented
- ✅ Documentation consolidated
- ✅ User manual created
- ✅ In-app help added
- ✅ CSV upload guide integrated
- ✅ Multi-currency guide integrated

**See full change log in SYSTEM_DOCUMENTATION.md**

---

## 🚦 Getting Started Checklist

**For New Installation:**

- [ ] Install Python dependencies (`pip install -r requirement.txt`)
- [ ] Configure database in `bss/settings.py`
- [ ] Run migrations (`python3 manage.py migrate`)
- [ ] Create superuser
- [ ] Load chart of accounts
- [ ] Configure currencies and exchange rates
- [ ] Set up banks, schools, departments
- [ ] Configure payroll account mappings
- [ ] Create user accounts
- [ ] Assign roles and permissions
- [ ] Test with sample data
- [ ] Train users
- [ ] Go live! 🎉

**For Daily Use:**

- [ ] Login to system
- [ ] Check notifications
- [ ] Process tasks (payroll, approvals, etc.)
- [ ] Review reports
- [ ] Logout when done

---

**Ready to use the system? Check out the [USER_MANUAL.md](USER_MANUAL.md)!** 📖

