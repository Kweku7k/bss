from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ledger.models import PettyCashFund, Account, Currency


class Command(BaseCommand):
    help = 'Set up initial petty cash funds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fund-name',
            type=str,
            default='Main Office Petty Cash',
            help='Name of the petty cash fund'
        )
        parser.add_argument(
            '--max-amount',
            type=float,
            default=500.00,
            help='Maximum amount for the fund'
        )
        parser.add_argument(
            '--custodian-username',
            type=str,
            help='Username of the custodian'
        )

    def handle(self, *args, **options):
        fund_name = options['fund_name']
        max_amount = options['max_amount']
        custodian_username = options['custodian_username']

        # Get or create base currency
        currency, created = Currency.objects.get_or_create(
            code='USD',
            defaults={
                'name': 'US Dollar',
                'symbol': '$',
                'decimal_places': 2,
                'is_active': True,
                'is_base_currency': True
            }
        )

        # Get or create petty cash account
        account, created = Account.objects.get_or_create(
            code='1100',
            defaults={
                'name': 'Petty Cash - Main Office',
                'type': 'ASSET',
                'currency': currency,
                'description': 'Main office petty cash fund',
                'is_active': True
            }
        )

        # Get custodian user
        custodian = None
        if custodian_username:
            try:
                custodian = User.objects.get(username=custodian_username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'User {custodian_username} not found. Using first superuser.')
                )

        if not custodian:
            custodian = User.objects.filter(is_superuser=True).first()

        if not custodian:
            self.stdout.write(
                self.style.ERROR('No users found. Please create a user first.')
            )
            return

        # Create petty cash fund
        fund, created = PettyCashFund.objects.get_or_create(
            name=fund_name,
            defaults={
                'account': account,
                'custodian': custodian,
                'maximum_amount': max_amount,
                'is_active': True
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created petty cash fund: {fund.name}'
                )
            )
            self.stdout.write(f'  - Account: {fund.account.name}')
            self.stdout.write(f'  - Custodian: {fund.custodian.get_full_name() or fund.custodian.username}')
            self.stdout.write(f'  - Maximum Amount: ${fund.maximum_amount}')
        else:
            self.stdout.write(
                self.style.WARNING(f'Petty cash fund {fund.name} already exists.')
            )

        # Create additional common funds
        additional_funds = [
            {
                'name': 'Department Petty Cash',
                'account_code': '1101',
                'account_name': 'Petty Cash - Department',
                'max_amount': 200.00
            },
            {
                'name': 'Travel Petty Cash',
                'account_code': '1102',
                'account_name': 'Petty Cash - Travel',
                'max_amount': 300.00
            }
        ]

        for fund_data in additional_funds:
            # Create account for this fund
            account, created = Account.objects.get_or_create(
                code=fund_data['account_code'],
                defaults={
                    'name': fund_data['account_name'],
                    'type': 'ASSET',
                    'currency': currency,
                    'description': f'{fund_data["name"]} account',
                    'is_active': True
                }
            )

            # Create fund
            fund, created = PettyCashFund.objects.get_or_create(
                name=fund_data['name'],
                defaults={
                    'account': account,
                    'custodian': custodian,
                    'maximum_amount': fund_data['max_amount'],
                    'is_active': True
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created fund: {fund.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('\nPetty cash funds setup completed!')
        )
