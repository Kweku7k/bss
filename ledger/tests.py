from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date

from .models import (
    Account, Journal, JournalLine, LedgerBalance,
    PettyCashFund, PettyCashVoucher
)
from .utils import post_journal_entry, generate_trial_balance

User = get_user_model()


class AccountModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_account_creation(self):
        """Test creating an account"""
        account = Account.objects.create(
            code='1000',
            name='Cash Account',
            type='ASSET',
            created_by=self.user
        )
        self.assertEqual(account.code, '1000')
        self.assertEqual(account.name, 'Cash Account')
        self.assertEqual(account.type, 'ASSET')
        self.assertTrue(account.is_active)
        
    def test_account_balance_type(self):
        """Test account balance type calculation"""
        asset_account = Account.objects.create(
            code='1000',
            name='Cash Account',
            type='ASSET',
            created_by=self.user
        )
        expense_account = Account.objects.create(
            code='4000',
            name='Office Supplies',
            type='EXPENSE',
            created_by=self.user
        )
        liability_account = Account.objects.create(
            code='2000',
            name='Accounts Payable',
            type='LIABILITY',
            created_by=self.user
        )
        
        self.assertEqual(asset_account.get_balance_type(), 'DEBIT')
        self.assertEqual(expense_account.get_balance_type(), 'DEBIT')
        self.assertEqual(liability_account.get_balance_type(), 'CREDIT')


class JournalModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.cash_account = Account.objects.create(
            code='1000',
            name='Cash Account',
            type='ASSET',
            created_by=self.user
        )
        
        self.income_account = Account.objects.create(
            code='3000',
            name='Tuition Income',
            type='INCOME',
            created_by=self.user
        )
        
    def test_journal_creation(self):
        """Test creating a journal entry"""
        journal = Journal.objects.create(
            date=date.today(),
            description='Test transaction',
            source_module='MANUAL',
            created_by=self.user
        )
        
        self.assertIsNotNone(journal.reference_no)
        self.assertEqual(journal.status, 'DRAFT')
        
    def test_journal_balancing(self):
        """Test journal balancing validation"""
        journal = Journal.objects.create(
            date=date.today(),
            description='Test transaction',
            source_module='MANUAL',
            created_by=self.user
        )
        
        # Create balanced journal lines
        JournalLine.objects.create(
            journal=journal,
            account=self.cash_account,
            debit=Decimal('1000.00')
        )
        
        JournalLine.objects.create(
            journal=journal,
            account=self.income_account,
            credit=Decimal('1000.00')
        )
        
        self.assertTrue(journal.is_balanced())
        self.assertEqual(journal.get_total_debit(), Decimal('1000.00'))
        self.assertEqual(journal.get_total_credit(), Decimal('1000.00'))


class LedgerBalanceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.asset_account = Account.objects.create(
            code='1000',
            name='Cash Account',
            type='ASSET',
            created_by=self.user
        )
        
        self.liability_account = Account.objects.create(
            code='2000',
            name='Accounts Payable',
            type='LIABILITY',
            created_by=self.user
        )
        
    def test_asset_account_balance_calculation(self):
        """Test closing balance calculation for asset accounts"""
        balance = LedgerBalance.objects.create(
            account=self.asset_account,
            opening_balance=Decimal('1000.00'),
            total_debit=Decimal('500.00'),
            total_credit=Decimal('200.00')
        )
        
        # Assets increase with debits: 1000 + 500 - 200 = 1300
        expected_balance = Decimal('1300.00')
        self.assertEqual(balance.closing_balance, expected_balance)
        
    def test_liability_account_balance_calculation(self):
        """Test closing balance calculation for liability accounts"""
        balance = LedgerBalance.objects.create(
            account=self.liability_account,
            opening_balance=Decimal('1000.00'),
            total_debit=Decimal('200.00'),
            total_credit=Decimal('500.00')
        )
        
        # Liabilities increase with credits: 1000 - 200 + 500 = 1300
        expected_balance = Decimal('1300.00')
        self.assertEqual(balance.closing_balance, expected_balance)


class PettyCashModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.cash_account = Account.objects.create(
            code='1000',
            name='Petty Cash',
            type='ASSET',
            created_by=self.user
        )
        
        self.expense_account = Account.objects.create(
            code='4000',
            name='Office Supplies',
            type='EXPENSE',
            created_by=self.user
        )
        
    def test_petty_cash_fund_creation(self):
        """Test creating a petty cash fund"""
        fund = PettyCashFund.objects.create(
            name='Main Office Petty Cash',
            account=self.cash_account,
            custodian=self.user,
            max_amount=Decimal('2000.00'),
            created_by=self.user
        )
        
        self.assertEqual(fund.name, 'Main Office Petty Cash')
        self.assertEqual(fund.max_amount, Decimal('2000.00'))
        self.assertTrue(fund.is_active)
        
    def test_petty_cash_voucher_creation(self):
        """Test creating a petty cash voucher"""
        fund = PettyCashFund.objects.create(
            name='Main Office Petty Cash',
            account=self.cash_account,
            custodian=self.user,
            max_amount=Decimal('2000.00'),
            current_balance=Decimal('1000.00'),
            created_by=self.user
        )
        
        voucher = PettyCashVoucher.objects.create(
            fund=fund,
            date=date.today(),
            amount=Decimal('100.00'),
            description='Office supplies',
            account=self.expense_account,
            requested_by=self.user
        )
        
        self.assertIsNotNone(voucher.voucher_no)
        self.assertEqual(voucher.status, 'PENDING')
        self.assertTrue(voucher.can_approve())


class UtilityFunctionsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.cash_account = Account.objects.create(
            code='1000',
            name='Cash Account',
            type='ASSET',
            created_by=self.user
        )
        
        self.income_account = Account.objects.create(
            code='3000',
            name='Tuition Income',
            type='INCOME',
            created_by=self.user
        )
        
    def test_post_journal_entry(self):
        """Test posting a journal entry"""
        journal = Journal.objects.create(
            date=date.today(),
            description='Test transaction',
            source_module='MANUAL',
            created_by=self.user
        )
        
        # Create balanced journal lines
        JournalLine.objects.create(
            journal=journal,
            account=self.cash_account,
            debit=Decimal('1000.00')
        )
        
        JournalLine.objects.create(
            journal=journal,
            account=self.income_account,
            credit=Decimal('1000.00')
        )
        
        # Post the journal
        post_journal_entry(journal, self.user)
        
        # Check that journal status changed
        journal.refresh_from_db()
        self.assertEqual(journal.status, 'POSTED')
        self.assertIsNotNone(journal.posted_at)
        
        # Check that ledger balances were updated
        cash_balance = LedgerBalance.objects.get(account=self.cash_account)
        income_balance = LedgerBalance.objects.get(account=self.income_account)
        
        self.assertEqual(cash_balance.total_debit, Decimal('1000.00'))
        self.assertEqual(income_balance.total_credit, Decimal('1000.00'))
        
    def test_generate_trial_balance(self):
        """Test generating trial balance"""
        # Create some transactions first
        journal = Journal.objects.create(
            date=date.today(),
            description='Test transaction',
            source_module='MANUAL',
            created_by=self.user,
            status='POSTED'
        )
        
        JournalLine.objects.create(
            journal=journal,
            account=self.cash_account,
            debit=Decimal('1000.00')
        )
        
        JournalLine.objects.create(
            journal=journal,
            account=self.income_account,
            credit=Decimal('1000.00')
        )
        
        # Post the journal
        post_journal_entry(journal, self.user)
        
        # Generate trial balance
        trial_balance = generate_trial_balance(date.today())
        
        self.assertIsNotNone(trial_balance)
        self.assertEqual(trial_balance['total_debit'], Decimal('1000.00'))
        self.assertEqual(trial_balance['total_credit'], Decimal('1000.00'))