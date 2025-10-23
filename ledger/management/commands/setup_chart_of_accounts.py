from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from ledger.models import Account

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up initial chart of accounts for the university ERP system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-username',
            type=str,
            default='admin',
            help='Username of the admin user to set as creator'
        )

    def handle(self, *args, **options):
        admin_username = options['admin_username']
        
        try:
            admin_user = User.objects.get(username=admin_username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Admin user "{admin_username}" not found. Please create an admin user first.')
            )
            return

        # Define the chart of accounts structure
        accounts_data = [
            # Assets
            {'code': '1000', 'name': 'Assets', 'type': 'HEADER', 'parent': None},
            {'code': '1100', 'name': 'Current Assets', 'type': 'HEADER', 'parent': '1000'},
            {'code': '1110', 'name': 'Cash at Main Office', 'type': 'ASSET', 'parent': '1100', 'description': 'Petty cash float'},
            {'code': '1120', 'name': 'Bank Account (GCB)', 'type': 'ASSET', 'parent': '1100', 'description': 'University main account'},
            {'code': '1130', 'name': 'Accounts Receivable', 'type': 'ASSET', 'parent': '1100', 'description': 'Student fees receivable'},
            {'code': '1140', 'name': 'Prepaid Expenses', 'type': 'ASSET', 'parent': '1100'},
            {'code': '1200', 'name': 'Fixed Assets', 'type': 'HEADER', 'parent': '1000'},
            {'code': '1210', 'name': 'Buildings', 'type': 'ASSET', 'parent': '1200'},
            {'code': '1220', 'name': 'Equipment', 'type': 'ASSET', 'parent': '1200'},
            {'code': '1230', 'name': 'Furniture & Fixtures', 'type': 'ASSET', 'parent': '1200'},
            {'code': '1240', 'name': 'Accumulated Depreciation', 'type': 'ASSET', 'parent': '1200', 'description': 'Contra asset account'},

            # Liabilities
            {'code': '2000', 'name': 'Liabilities', 'type': 'HEADER', 'parent': None},
            {'code': '2100', 'name': 'Current Liabilities', 'type': 'HEADER', 'parent': '2000'},
            {'code': '2110', 'name': 'Student Deposits', 'type': 'LIABILITY', 'parent': '2100', 'description': 'Advance payments'},
            {'code': '2120', 'name': 'Accounts Payable', 'type': 'LIABILITY', 'parent': '2100'},
            {'code': '2130', 'name': 'Accrued Expenses', 'type': 'LIABILITY', 'parent': '2100'},
            {'code': '2140', 'name': 'Payroll Liabilities', 'type': 'LIABILITY', 'parent': '2100', 'description': 'PAYE, SSNIT, etc.'},
            {'code': '2200', 'name': 'Long-term Liabilities', 'type': 'HEADER', 'parent': '2000'},
            {'code': '2210', 'name': 'Long-term Debt', 'type': 'LIABILITY', 'parent': '2200'},

            # Equity
            {'code': '3000', 'name': 'Equity', 'type': 'HEADER', 'parent': None},
            {'code': '3100', 'name': 'Retained Earnings', 'type': 'EQUITY', 'parent': '3000'},
            {'code': '3200', 'name': 'Current Year Surplus', 'type': 'EQUITY', 'parent': '3000'},

            # Income
            {'code': '4000', 'name': 'Income', 'type': 'HEADER', 'parent': None},
            {'code': '4100', 'name': 'Tuition Income', 'type': 'INCOME', 'parent': '4000'},
            {'code': '4110', 'name': 'Undergraduate Tuition', 'type': 'INCOME', 'parent': '4100'},
            {'code': '4120', 'name': 'Graduate Tuition', 'type': 'INCOME', 'parent': '4100'},
            {'code': '4200', 'name': 'Other Income', 'type': 'INCOME', 'parent': '4000'},
            {'code': '4210', 'name': 'Library Fees', 'type': 'INCOME', 'parent': '4200'},
            {'code': '4220', 'name': 'Examination Fees', 'type': 'INCOME', 'parent': '4200'},
            {'code': '4230', 'name': 'Late Fees', 'type': 'INCOME', 'parent': '4200'},

            # Expenses
            {'code': '5000', 'name': 'Expenses', 'type': 'HEADER', 'parent': None},
            {'code': '5100', 'name': 'Personnel Expenses', 'type': 'EXPENSE', 'parent': '5000'},
            {'code': '5110', 'name': 'Salaries', 'type': 'EXPENSE', 'parent': '5100'},
            {'code': '5120', 'name': 'Benefits', 'type': 'EXPENSE', 'parent': '5100'},
            {'code': '5130', 'name': 'Bonuses', 'type': 'EXPENSE', 'parent': '5100'},
            {'code': '5200', 'name': 'Operating Expenses', 'type': 'EXPENSE', 'parent': '5000'},
            {'code': '5210', 'name': 'Utilities', 'type': 'EXPENSE', 'parent': '5200', 'description': 'Water, electricity'},
            {'code': '5220', 'name': 'Office Supplies', 'type': 'EXPENSE', 'parent': '5200'},
            {'code': '5230', 'name': 'Printing & Stationery', 'type': 'EXPENSE', 'parent': '5200'},
            {'code': '5240', 'name': 'Telecommunications', 'type': 'EXPENSE', 'parent': '5200'},
            {'code': '5300', 'name': 'Academic Expenses', 'type': 'EXPENSE', 'parent': '5000'},
            {'code': '5310', 'name': 'Library Materials', 'type': 'EXPENSE', 'parent': '5300'},
            {'code': '5320', 'name': 'Laboratory Supplies', 'type': 'EXPENSE', 'parent': '5300'},
            {'code': '5400', 'name': 'Administrative Expenses', 'type': 'EXPENSE', 'parent': '5000'},
            {'code': '5410', 'name': 'Insurance', 'type': 'EXPENSE', 'parent': '5400'},
            {'code': '5420', 'name': 'Legal Fees', 'type': 'EXPENSE', 'parent': '5400'},
            {'code': '5430', 'name': 'Audit Fees', 'type': 'EXPENSE', 'parent': '5400'},
        ]

        created_count = 0
        updated_count = 0

        for account_data in accounts_data:
            parent_code = account_data.pop('parent')
            parent = None
            
            if parent_code:
                try:
                    parent = Account.objects.get(code=parent_code)
                except Account.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Parent account {parent_code} not found for {account_data["code"]}')
                    )

            account, created = Account.objects.get_or_create(
                code=account_data['code'],
                defaults={
                    'name': account_data['name'],
                    'type': account_data['type'],
                    'parent': parent,
                    'description': account_data.get('description', ''),
                    'created_by': admin_user,
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created account: {account.code} - {account.name}')
                )
            else:
                # Update existing account
                account.name = account_data['name']
                account.type = account_data['type']
                account.parent = parent
                account.description = account_data.get('description', '')
                account.is_active = True
                account.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated account: {account.code} - {account.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nChart of accounts setup completed!\n'
                f'Created: {created_count} accounts\n'
                f'Updated: {updated_count} accounts\n'
                f'Total: {created_count + updated_count} accounts'
            )
        )

        # Display account hierarchy
        self.stdout.write('\nAccount Hierarchy:')
        self.display_hierarchy()

    def display_hierarchy(self, parent=None, level=0):
        """Display the account hierarchy"""
        accounts = Account.objects.filter(parent=parent, is_active=True).order_by('code')
        
        for account in accounts:
            indent = '  ' * level
            self.stdout.write(f'{indent}{account.code} - {account.name} ({account.type})')
            
            # Recursively display children
            self.display_hierarchy(account, level + 1)

