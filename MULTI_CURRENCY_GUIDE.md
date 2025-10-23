# Multi-Currency Exchange Rate Usage Guide

## How Exchange Rates Work in the General Ledger System

### 1. **Setting Up Currencies and Exchange Rates**

First, you need to set up your currencies and exchange rates:

#### Step 1: Create Currencies
1. Go to **General Ledger > Currency Management**
2. Click **Add Currency**
3. Create currencies like:
   - **GHS** (Ghana Cedi) - Set as Base Currency
   - **USD** (US Dollar)
   - **EUR** (Euro)
   - **GBP** (British Pound)

#### Step 2: Set Exchange Rates
1. Go to **General Ledger > Currency Management > Exchange Rates**
2. Add exchange rates for different dates:

```
From: USD, To: GHS, Rate: 12.50, Date: 2024-01-01
From: EUR, To: GHS, Rate: 13.75, Date: 2024-01-01
From: GBP, To: GHS, Rate: 15.25, Date: 2024-01-01
```

### 2. **Creating Multi-Currency Accounts**

When creating accounts, you can specify different currencies:

```
Account Code: 1100, Name: Cash - USD, Type: ASSET, Currency: USD
Account Code: 1200, Name: Cash - EUR, Type: ASSET, Currency: EUR
Account Code: 1300, Name: Cash - GHS, Type: ASSET, Currency: GHS (Base)
```

### 3. **Recording Multi-Currency Transactions**

#### Example: International Student Payment
A student pays $1,000 USD tuition fee:

**Journal Entry:**
- **Date:** 2024-01-15
- **Description:** International student tuition payment
- **Source Module:** STUDENT_FEES

**Journal Lines:**
```
Line 1: Debit Cash - USD (1100) $1,000.00 USD
Line 2: Credit Tuition Income (4100) $1,000.00 USD
```

**What Happens Automatically:**
1. System records $1,000 in USD
2. Gets exchange rate USD to GHS: 12.50
3. Calculates base currency amount: $1,000 × 12.50 = ₵12,500
4. Updates both USD and GHS balances

### 4. **Exchange Rate Conversion in Practice**

#### Scenario: Mixed Currency Transaction
You receive payment in multiple currencies:

**Journal Entry:**
- **Date:** 2024-01-20
- **Description:** Mixed currency payment from international students

**Journal Lines:**
```
Line 1: Debit Cash - USD (1100) $500.00 USD
Line 2: Debit Cash - EUR (1200) €300.00 EUR  
Line 3: Credit Tuition Income (4100) ₵10,375.00 GHS
```

**Automatic Conversions:**
- USD $500 × 12.50 = ₵6,250 (Base)
- EUR €300 × 13.75 = ₵4,125 (Base)
- Total Base: ₵6,250 + ₵4,125 = ₵10,375

### 5. **Reporting with Multi-Currency**

#### Trial Balance Report
Shows balances in both original currency and base currency:

```
Account          | Original Amount | Currency | Base Amount | Base Currency
-----------------|-----------------|----------|-------------|---------------
Cash - USD       | $1,500.00       | USD      | ₵18,750.00  | GHS
Cash - EUR       | €800.00         | EUR      | ₵11,000.00  | GHS
Cash - GHS       | ₵5,000.00       | GHS      | ₵5,000.00   | GHS
```

#### Balance Sheet Report
All amounts converted to base currency for consolidated reporting:

```
ASSETS
Cash and Cash Equivalents: ₵34,750.00 (GHS)

LIABILITIES & EQUITY
Total Liabilities & Equity: ₵34,750.00 (GHS)
```

### 6. **Exchange Rate Updates**

#### Historical Rates
You can set different rates for different periods:

```
USD to GHS: 12.50 (Jan 1, 2024)
USD to GHS: 12.75 (Feb 1, 2024)
USD to GHS: 13.00 (Mar 1, 2024)
```

#### Impact on Reports
- **January transactions:** Use 12.50 rate
- **February transactions:** Use 12.75 rate
- **March transactions:** Use 13.00 rate

### 7. **Practical Examples**

#### Example 1: International Vendor Payment
```
Transaction: Pay $2,000 to US vendor
Exchange Rate: USD to GHS = 12.50

Journal Entry:
Debit: Accounts Payable - USD $2,000.00
Credit: Cash - USD $2,000.00

Base Currency Impact:
Debit: Accounts Payable ₵25,000.00
Credit: Cash ₵25,000.00
```

#### Example 2: Currency Exchange Loss/Gain
```
Scenario: USD rate changes from 12.50 to 13.00
You have $1,000 in USD account

Original Value: $1,000 × 12.50 = ₵12,500
New Value: $1,000 × 13.00 = ₵13,000
Gain: ₵500

Journal Entry:
Debit: Cash - USD $1,000.00
Credit: Exchange Gain ₵500.00
```

### 8. **Best Practices**

1. **Set Base Currency First:** Always set your local currency as base
2. **Update Rates Regularly:** Keep exchange rates current
3. **Use Historical Rates:** For accurate historical reporting
4. **Monitor Currency Exposure:** Track foreign currency balances
5. **Document Exchange Policies:** Have clear currency conversion policies

### 9. **System Benefits**

- **Automatic Conversion:** No manual calculations needed
- **Dual Reporting:** See both original and converted amounts
- **Historical Accuracy:** Maintain original currency amounts
- **Audit Trail:** Complete transaction history
- **Compliance:** Meets international accounting standards

### 10. **Troubleshooting**

#### Common Issues:
1. **Missing Exchange Rate:** System defaults to 1.000000
2. **Currency Mismatch:** Journal line currency must match account currency
3. **Rate Updates:** Old transactions keep original rates
4. **Base Currency:** Only one currency can be base

#### Solutions:
1. Set up exchange rates for all active currencies
2. Validate currency consistency in forms
3. Use historical rates for accurate reporting
4. Ensure base currency is properly configured

This multi-currency system provides complete flexibility for international transactions while maintaining accurate reporting and compliance with accounting standards.