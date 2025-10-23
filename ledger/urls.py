from django.urls import path
from . import views

app_name = 'ledger'

urlpatterns = [
    # Chart of Accounts
    path('accounts/', views.chart_of_accounts, name='chart_of_accounts'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/bulk-create/', views.bulk_account_create, name='bulk_account_create'),
    path('accounts/<int:account_id>/', views.account_detail, name='account_detail'),
    path('accounts/<int:account_id>/edit/', views.account_edit, name='account_edit'),
    path('accounts/<int:account_id>/delete/', views.account_delete, name='account_delete'),
    
    # Journal Entries
    path('journals/', views.journal_list, name='journal_list'),
    path('journals/create/', views.journal_create, name='journal_create'),
    path('journals/<uuid:journal_id>/', views.journal_detail, name='journal_detail'),
    path('journals/<uuid:journal_id>/post/', views.journal_post, name='journal_post'),
    
    # Petty Cash
    path('petty-cash/', views.petty_cash_funds, name='petty_cash_funds'),
    path('petty-cash/create/', views.petty_cash_fund_create, name='petty_cash_fund_create'),
    path('petty-cash/<int:fund_id>/', views.petty_cash_fund_detail, name='petty_cash_fund_detail'),
    path('petty-cash/<int:fund_id>/replenish/', views.petty_cash_fund_replenish, name='petty_cash_fund_replenish'),
    path('petty-cash/vouchers/create/', views.petty_cash_voucher_create, name='petty_cash_voucher_create'),
    path('petty-cash/vouchers/<int:voucher_id>/', views.petty_cash_voucher_detail, name='petty_cash_voucher_detail'),
    path('petty-cash/vouchers/<int:voucher_id>/approve/', views.petty_cash_voucher_approve, name='petty_cash_voucher_approve'),
    
    # Reports
    path('reports/trial-balance/', views.reports_trial_balance, name='reports_trial_balance'),
    path('reports/ledger-detail/', views.reports_ledger_detail, name='reports_ledger_detail'),
    path('reports/journal-listing/', views.reports_journal_listing, name='reports_journal_listing'),
    path('reports/balance-sheet/', views.reports_balance_sheet, name='reports_balance_sheet'),
    path('reports/profit-loss/', views.reports_profit_loss, name='reports_profit_loss'),
    
    # Currency Management
    path('currencies/', views.currency_list, name='currency_list'),
    path('currencies/create/', views.currency_create, name='currency_create'),
    path('currencies/<int:currency_id>/edit/', views.currency_edit, name='currency_edit'),
    path('exchange-rates/', views.exchange_rate_list, name='exchange_rate_list'),
    path('exchange-rates/create/', views.exchange_rate_create, name='exchange_rate_create'),
    
    # Budget Management
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/create/', views.budget_create, name='budget_create'),
    path('budgets/<int:budget_id>/', views.budget_detail, name='budget_detail'),
    path('budgets/<int:budget_id>/edit/', views.budget_edit, name='budget_edit'),
    path('budgets/<int:budget_id>/approve/', views.budget_approve, name='budget_approve'),
    path('budgets/reports/', views.budget_reports, name='budget_reports'),
    
    # API endpoints
    path('api/parent-accounts/', views.api_parent_accounts, name='api_parent_accounts'),
    # path('api/account/<int:account_id>/balance/', views.api_account_balance, name='api_account_balance'),
    path('api/fund/<int:fund_id>/balance/', views.api_fund_balance, name='api_fund_balance'),
]
