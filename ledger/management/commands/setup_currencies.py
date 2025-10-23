from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from ledger.models import Currency, Account

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up initial currencies for the university ERP system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-username',
            type=str,
            default='admin',
            help='Username of the admin user to set as creator'
        )

    def handle(self, *args, **kwargs):
        admin_username = kwargs['admin_username']
        
        try:
            admin_user = User.objects.get(username=admin_username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Admin user "{admin_username}" not found. Please create an admin user first.')
            )
            return

        # Define common currencies for universities
        currencies_data = [
            {
                'code': 'GHS',
                'name': 'Ghana Cedi',
                'symbol': '₵',
                'decimal_places': 2,
                'is_base_currency': True,
                'is_active': True
            },
            {
                'code': 'USD',
                'name': 'US Dollar',
                'symbol': '$',
                'decimal_places': 2,
                'is_base_currency': False,
                'is_active': True
            },
            {
                'code': 'EUR',
                'name': 'Euro',
                'symbol': '€',
                'decimal_places': 2,
                'is_base_currency': False,
                'is_active': True
            },
            {
                'code': 'GBP',
                'name': 'British Pound',
                'symbol': '£',
                'decimal_places': 2,
                'is_base_currency': False,
                'is_active': True
            },
            {
                'code': 'NGN',
                'name': 'Nigerian Naira',
                'symbol': '₦',
                'decimal_places': 2,
                'is_base_currency': False,
                'is_active': True
            },
            {
                'code': 'KES',
                'name': 'Kenyan Shilling',
                'symbol': 'KSh',
                'decimal_places': 2,
                'is_base_currency': False,
                'is_active': True
            },
            {
                'code': 'ZAR',
                'name': 'South African Rand',
                'symbol': 'R',
                'decimal_places': 2,
                'is_base_currency': False,
                'is_active': True
            },
        ]

        created_count = 0
        updated_count = 0

        for currency_data in currencies_data:
            currency, created = Currency.objects.get_or_create(
                code=currency_data['code'],
                defaults=currency_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created currency: {currency.code} - {currency.name}')
                )
            else:
                # Update existing currency
                for key, value in currency_data.items():
                    setattr(currency, key, value)
                currency.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated currency: {currency.code} - {currency.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCurrency setup completed!\n'
                f'Created: {created_count} currencies\n'
                f'Updated: {updated_count} currencies\n'
                f'Total: {created_count + updated_count} currencies'
            )
        )

        # Display currency list
        self.stdout.write('\nActive Currencies:')
        currencies = Currency.objects.filter(is_active=True).order_by('code')
        for currency in currencies:
            base_indicator = ' (BASE)' if currency.is_base_currency else ''
            self.stdout.write(f'{currency.code} - {currency.name} {currency.symbol}{base_indicator}')

