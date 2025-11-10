# Documentation Index

**Central University ERP System**  
**Last Updated:** November 4, 2025

---

## 📚 Available Documentation

### **Main Documentation Files**

#### 1. **SYSTEM_DOCUMENTATION.md** 📖
**For:** System Administrators, Developers, Finance Officers  
**Contents:**
- Complete system overview
- All modules and features
- Technical reference
- Database models
- API/functions reference
- Troubleshooting guide
- Maintenance procedures

**When to use:** 
- Setting up the system
- Technical configuration
- Understanding system architecture
- Troubleshooting technical issues

---

#### 2. **USER_MANUAL.md** 👤
**For:** All End Users (Staff, HR Officers, Finance Officers, Managers)  
**Contents:**
- User-friendly guides for common tasks
- Step-by-step instructions
- Screenshots and examples
- FAQ and troubleshooting
- Role-based sections

**When to use:**
- Daily operations
- Learning how to use features
- Quick reference
- Teaching new users

**Access in App:** 
- Click **"User Manual"** in the sidebar (bottom left)
- URL: `/help/manual/`

---

### **Supplementary Documentation**

#### 3. **general_ledger_module.md**
**Focus:** Detailed General Ledger technical reference  
**Topics:** Accounts, journals, petty cash, financial reports

#### 4. **ledger/README.md**
**Focus:** Ledger module installation and setup  
**Topics:** Migration, initial setup, admin interface

---

## 🗂️ Documentation Organization

### Current Structure (Clean!)

```
/Users/mrsoftlife/Documents/Projects/bss/
├── SYSTEM_DOCUMENTATION.md       ⭐ Main technical docs
├── USER_MANUAL.md                ⭐ User-friendly guide
├── DOCUMENTATION_INDEX.md        📍 This file
├── general_ledger_module.md      📊 Ledger details
├── ledger/README.md              📖 Ledger module
└── requirement.txt               📦 Dependencies
```

### What Was Removed (15 files consolidated)

All content from these files has been merged into the main docs:
- ❌ PAYROLL_JOURNAL_SYSTEM.md → SYSTEM_DOCUMENTATION.md
- ❌ PAYROLL_JOURNAL_QUICKSTART.md → USER_MANUAL.md
- ❌ EXCHANGE_RATE_SYSTEM.md → SYSTEM_DOCUMENTATION.md
- ❌ MULTI_CURRENCY_GUIDE.md → SYSTEM_DOCUMENTATION.md + USER_MANUAL.md
- ❌ CSV_UPLOAD_GUIDE.md → SYSTEM_DOCUMENTATION.md + USER_MANUAL.md
- ❌ JOURNAL_SYSTEM_COMPLETE.md → SYSTEM_DOCUMENTATION.md
- ❌ JOURNAL_LINE_DATE_UPDATE.md → SYSTEM_DOCUMENTATION.md
- ❌ CLEAN_JOURNAL_SUMMARY.md → SYSTEM_DOCUMENTATION.md
- ❌ FINAL_JOURNAL_DESIGN.md → SYSTEM_DOCUMENTATION.md
- ❌ PROFESSIONAL_JOURNAL_UPDATE.md → SYSTEM_DOCUMENTATION.md
- ❌ JOURNAL_UI_UPDATE.md → SYSTEM_DOCUMENTATION.md
- ❌ COST_CENTER_CORRECTION.md → SYSTEM_DOCUMENTATION.md
- ❌ COST_CENTER_FINAL.md → SYSTEM_DOCUMENTATION.md
- ❌ JOURNAL_IMPROVEMENTS.md → SYSTEM_DOCUMENTATION.md
- ❌ QUICK_START_GUIDE.md → SYSTEM_DOCUMENTATION.md + USER_MANUAL.md

---

## 📋 Quick Topic Finder

**Need to know about...**

| Topic | Find It In |
|-------|-----------|
| Login & Security | USER_MANUAL.md → Login & Security |
| Adding New Staff | USER_MANUAL.md → For HR Officers |
| Processing Payroll | USER_MANUAL.md → Processing Monthly Payroll |
| Generating Payroll Journal | SYSTEM_DOCUMENTATION.md → Section 6.1 |
| Creating Journal Entries | USER_MANUAL.md → For Finance Officers |
| Multi-Currency Transactions | USER_MANUAL.md → Creating Journal Entries |
| Exchange Rates Setup | SYSTEM_DOCUMENTATION.md → Section 6.2 |
| CSV Upload Accounts | SYSTEM_DOCUMENTATION.md → Section 6.3 |
| Chart of Accounts | SYSTEM_DOCUMENTATION.md → Section 6.4 |
| Leave Applications | USER_MANUAL.md → For Staff Users |
| Medical Claims | USER_MANUAL.md → For Staff Users |
| Financial Reports | USER_MANUAL.md → For Finance Officers |
| Account Mappings | SYSTEM_DOCUMENTATION.md → Section 6.1 |
| Database Models | SYSTEM_DOCUMENTATION.md → Section 8.1 |
| Troubleshooting | Both files have troubleshooting sections |

---

## 🔄 Updating Documentation

**When You Make System Changes:**

1. **Update SYSTEM_DOCUMENTATION.md:**
   - Add/modify technical details
   - Update Feature Change Log (bottom of file)
   - Update version number and date (top of file)

2. **Update USER_MANUAL.md (if user-facing):**
   - Add/modify user instructions
   - Update screenshots if applicable
   - Update version history (bottom of file)

3. **Update This Index (if needed):**
   - Add new documentation files
   - Update topic finder

---

## 🎯 For Different Audiences

### New Employee (Staff User)
**Start here:** USER_MANUAL.md
**Focus on:**
- Login & Security
- Updating Your Profile
- Applying for Leave
- Submitting Medical Claims
- Viewing Your Payslip

### New HR Officer
**Start here:** USER_MANUAL.md → For HR Officers
**Also read:** SYSTEM_DOCUMENTATION.md → Section 3.1 (HR Module)
**Focus on:**
- Adding new employees
- Processing payroll
- Managing staff income/deductions
- Approving leave

### New Finance Officer
**Start here:** USER_MANUAL.md → For Finance Officers
**Also read:** SYSTEM_DOCUMENTATION.md → Sections 6.1-6.4
**Focus on:**
- Creating journal entries
- Managing exchange rates
- Chart of accounts
- Financial reports
- Payroll journal generation

### System Administrator
**Start here:** SYSTEM_DOCUMENTATION.md (read all)
**Also read:** general_ledger_module.md, ledger/README.md
**Focus on:**
- Architecture & Technology Stack
- Database models
- Security & permissions
- Maintenance & updates

### Developer
**Start here:** SYSTEM_DOCUMENTATION.md → Section 8 (Technical Reference)
**Focus on:**
- Database models
- Key functions
- URL patterns
- API structure

---

## 📱 Accessing Help in the Application

Users can access help directly from within the system:

**Method 1: Sidebar Menu**
- Click **"User Manual"** (sidebar, near bottom)
- Full manual opens in browser

**Method 2: Direct URL**
- Go to: `/help/manual/`

**Method 3: Context Help (Future Enhancement)**
- Click "?" icon on any page
- See help specific to that page

---

## 🔍 Search Tips

**To find something quickly:**

1. **Use Ctrl+F** (or Cmd+F) to search within a document
2. **Check the Table of Contents** at the top of each doc
3. **Use the Topic Finder** table above
4. **Check both SYSTEM_DOCUMENTATION.md and USER_MANUAL.md** - they complement each other

---

## 📊 Documentation Statistics

| Metric | Count |
|--------|-------|
| Total Documentation Files | 5 main files |
| Total Pages (combined) | ~50+ pages |
| Modules Documented | 5 (HR, Ledger, Setup, Leave, Medical) |
| Features Documented | 100+ features |
| Step-by-Step Guides | 30+ guides |
| Code Examples | 50+ examples |

---

## 🎓 Training Recommendation

**For New Users:**
1. Read USER_MANUAL.md (30 minutes)
2. Practice with test data (1 hour)
3. Shadow experienced user (2 hours)
4. Start with supervised access (1 week)

**For System Administrators:**
1. Read SYSTEM_DOCUMENTATION.md (2 hours)
2. Read general_ledger_module.md (30 minutes)
3. Set up test environment (2 hours)
4. Practice all workflows (4 hours)

---

## 📞 Support Resources

**Online:**
- 📖 Documentation files (this folder)
- 🌐 In-app manual: `/help/manual/`
- 📧 Email: helpdesk@central.edu.gh

**Offline:**
- 📞 Help Desk: [Your phone number]
- 🏢 IT Office: [Location]
- ⏰ Office Hours: Mon-Fri 8AM-5PM

---

## ✅ Documentation Quality Checklist

When updating documentation:
- [ ] Information is accurate and tested
- [ ] Examples are real and relevant
- [ ] Screenshots are current (if applicable)
- [ ] Links work correctly
- [ ] Language is clear and simple
- [ ] Technical terms are explained
- [ ] Version and date are updated
- [ ] Change log is updated

---

**This index helps you navigate all documentation efficiently. Bookmark it!** 🔖

*Last reviewed: November 4, 2025*

