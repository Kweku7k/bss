from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ledger.models import Currency, ExchangeRate
from decimal import Decimal
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Set up initial currencies and exchange rates for the General Ledger system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-username',
            type=str,
            default='admin',
            help='Username of the admin user (default: admin)'
        )
        parser.add_argument(
            '--base-currency',
            type=str,
            default='GHS',
            help='Base currency code (default: GHS)'
        )

    def handle(self, *args, **options):
        admin_username = options['admin_username']
        base_currency_code = options['base_currency']
        
        try:
            admin_user = User.objects.get(username=admin_username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Admin user "{admin_username}" not found. Please create an admin user first.')
            )
            return

        # Create currencies
        currencies_data = [
            {
                'code': 'GHS',
                'name': 'Ghana Cedi',
                'symbol': '₵',
                'decimal_places': 2,
                'is_base_currency': base_currency_code == 'GHS',
                'is_active': True
            },
            {
                'code': 'USD',
                'name': 'US Dollar',
                'symbol': '$',
                'decimal_places': 2,
                'is_base_currency': base_currency_code == 'USD',
                'is_active': True
            },
            {
                'code': 'EUR',
                'name': 'Euro',
                'symbol': '€',
                'decimal_places': 2,
                'is_base_currency': base_currency_code == 'EUR',
                'is_active': True
            },
            {
                'code': 'GBP',
                'name': 'British Pound',
                'symbol': '£',
                'decimal_places': 2,
                'is_base_currency': base_currency_code == 'GBP',
                'is_active': True
            },
            {
                'code': 'JPY',
                'name': 'Japanese Yen',
                'symbol': '¥',
                'decimal_places': 0,
                'is_base_currency': base_currency_code == 'JPY',
                'is_active': True
            }
        ]

        self.stdout.write('Creating currencies...')
        created_currencies = {}
        
        for currency_data in currencies_data:
            currency, created = Currency.objects.get_or_create(
                code=currency_data['code'],
                defaults=currency_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created currency: {currency.code} - {currency.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Currency already exists: {currency.code} - {currency.name}')
                )
            created_currencies[currency.code] = currency

        # Create exchange rates
        self.stdout.write('\nCreating exchange rates...')
        
        # Get base currency
        base_currency = created_currencies[base_currency_code]
        
        # Exchange rates (as of a sample date)
        exchange_rates_data = [
            # USD rates
            {'from': 'USD', 'to': 'GHS', 'rate': Decimal('12.50')},
            {'from': 'USD', 'to': 'EUR', 'rate': Decimal('0.85')},
            {'from': 'USD', 'to': 'GBP', 'rate': Decimal('0.75')},
            {'from': 'USD', 'to': 'JPY', 'rate': Decimal('110.00')},
            
            # EUR rates
            {'from': 'EUR', 'to': 'GHS', 'rate': Decimal('14.70')},
            {'from': 'EUR', 'to': 'USD', 'rate': Decimal('1.18')},
            {'from': 'EUR', 'to': 'GBP', 'rate': Decimal('0.88')},
            {'from': 'EUR', 'to': 'JPY', 'rate': Decimal('129.50')},
            
            # GBP rates
            {'from': 'GBP', 'to': 'GHS', 'rate': Decimal('16.70')},
            {'from': 'GBP', 'to': 'USD', 'rate': Decimal('1.33')},
            {'from': 'GBP', 'to': 'EUR', 'rate': Decimal('1.14')},
            {'from': 'GBP', 'to': 'JPY', 'rate': Decimal('146.50')},
            
            # JPY rates
            {'from': 'JPY', 'to': 'GHS', 'rate': Decimal('0.114')},
            {'from': 'JPY', 'to': 'USD', 'rate': Decimal('0.0091')},
            {'from': 'JPY', 'to': 'EUR', 'rate': Decimal('0.0077')},
            {'from': 'JPY', 'to': 'GBP', 'rate': Decimal('0.0068')},
        ]

        # Create exchange rates for different dates
        dates = [
            date.today() - timedelta(days=30),  # 30 days ago
            date.today() - timedelta(days=15),  # 15 days ago
            date.today(),                       # Today
        ]

        for rate_data in exchange_rates_data:
            from_currency = created_currencies[rate_data['from']]
            to_currency = created_currencies[rate_data['to']]
            
            for rate_date in dates:
                # Add some variation to rates for different dates
                rate_variation = Decimal('0.05') if rate_date == date.today() else Decimal('0')
                adjusted_rate = rate_data['rate'] + rate_variation
                
                exchange_rate, created = ExchangeRate.objects.get_or_create(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    effective_date=rate_date,
                    defaults={
                        'rate': adjusted_rate,
                        'is_active': True,
                        'created_by': admin_user
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Created exchange rate: {from_currency.code} to {to_currency.code} '
                            f'= {adjusted_rate} (Date: {rate_date})'
                        )
                    )

        # Create sample accounts with different currencies
        self.stdout.write('\nCreating sample multi-currency accounts...')
        
        from ledger.models import Account
        
        sample_accounts = [
            {'code': '1100', 'name': 'Cash - GHS', 'type': 'ASSET', 'currency': 'GHS'},
            {'code': '1101', 'name': 'Cash - USD', 'type': 'ASSET', 'currency': 'USD'},
            {'code': '1102', 'name': 'Cash - EUR', 'type': 'ASSET', 'currency': 'EUR'},
            {'code': '1103', 'name': 'Cash - GBP', 'type': 'ASSET', 'currency': 'GBP'},
            {'code': '1200', 'name': 'Bank Account - GHS', 'type': 'ASSET', 'currency': 'GHS'},
            {'code': '1201', 'name': 'Bank Account - USD', 'type': 'ASSET', 'currency': 'USD'},
            {'code': '2100', 'name': 'Accounts Payable - GHS', 'type': 'LIABILITY', 'currency': 'GHS'},
            {'code': '2101', 'name': 'Accounts Payable - USD', 'type': 'LIABILITY', 'currency': 'USD'},
            {'code': '4100', 'name': 'Tuition Income - GHS', 'type': 'INCOME', 'currency': 'GHS'},
            {'code': '4101', 'name': 'Tuition Income - USD', 'type': 'INCOME', 'currency': 'USD'},
        ]

        for account_data in sample_accounts:
            account, created = Account.objects.get_or_create(
                code=account_data['code'],
                defaults={
                    'name': account_data['name'],
                    'type': account_data['type'],
                    'currency': created_currencies[account_data['currency']],
                    'is_active': True,
                    'created_by': admin_user
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created account: {account.code} - {account.name} ({account.currency.code})'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Multi-currency setup completed successfully!\n'
                f'Base currency: {base_currency.code} - {base_currency.name}\n'
                f'Total currencies: {len(created_currencies)}\n'
                f'Exchange rates created for multiple dates\n'
                f'Sample multi-currency accounts created\n\n'
                f'You can now:\n'
                f'1. Create journal entries in different currencies\n'
                f'2. View reports with automatic currency conversion\n'
                f'3. Manage exchange rates through the web interface\n'
                f'4. Track balances in both original and base currencies'
            )
        )