from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import *


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'decimal_places', 'is_active', 'is_base_currency']
    list_filter = ['is_active', 'is_base_currency']
    search_fields = ['code', 'name']
    ordering = ['code']
    list_editable = ['is_active', 'is_base_currency']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'symbol', 'decimal_places')
        }),
        ('Status', {
            'fields': ('is_active', 'is_base_currency')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['from_currency', 'to_currency', 'rate', 'effective_date', 'is_active']
    list_filter = ['is_active', 'effective_date', 'from_currency', 'to_currency']
    search_fields = ['from_currency__code', 'to_currency__code']
    ordering = ['-effective_date']
    
    fieldsets = (
        ('Exchange Rate Information', {
            'fields': ('from_currency', 'to_currency', 'rate', 'effective_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'type', 'currency', 'parent', 'is_active', 'created_at']
    list_filter = ['type', 'currency', 'is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    ordering = ['code']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'type', 'parent', 'currency', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class BudgetLineInline(admin.TabularInline):
    model = BudgetLine
    extra = 1
    fields = ['account', 'allocated_amount', 'description']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'fiscal_year', 'status', 'currency', 'total_budget', 'total_allocated', 'total_spent', 'utilization_percentage']
    list_filter = ['status', 'fiscal_year', 'currency', 'created_at']
    search_fields = ['name', 'description', 'fiscal_year']
    ordering = ['-fiscal_year', '-created_at']
    inlines = [BudgetLineInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'fiscal_year', 'description', 'currency', 'total_budget')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Audit', {
            'fields': ('created_by', 'approved_by', 'created_at', 'updated_at', 'approved_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'approved_at']

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    list_display = ['budget', 'account', 'allocated_amount', 'spent_amount', 'remaining_amount', 'utilization_percentage']
    list_filter = ['budget__fiscal_year', 'budget__status', 'account__type']
    search_fields = ['budget__name', 'account__code', 'account__name', 'description']
    ordering = ['budget', 'account__code']

    fieldsets = (
        ('Budget Line Information', {
            'fields': ('budget', 'account', 'allocated_amount', 'description')
        }),
        ('Calculated Fields', {
            'fields': ('spent_amount', 'remaining_amount', 'utilization_percentage'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['spent_amount', 'remaining_amount', 'utilization_percentage', 'created_at', 'updated_at']


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 2
    fields = ['account', 'debit', 'credit', 'currency', 'exchange_rate', 'description']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account', 'currency')


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['reference_no', 'date', 'description', 'source_module', 
                   'status', 'created_by', 'total_debit', 'total_credit', 'is_balanced']
    list_filter = ['status', 'source_module', 'date', 'created_at']
    search_fields = ['reference_no', 'description']
    ordering = ['-date', '-created_at']
    inlines = [JournalLineInline]
    
    fieldsets = (
        ('Journal Information', {
            'fields': ('reference_no', 'date', 'description', 'source_module')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at', 'posted_at', 'posted_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['reference_no', 'created_at', 'updated_at', 'posted_at']
    
    def total_debit(self, obj):
        return obj.get_total_debit()
    total_debit.short_description = 'Total Debit'
    
    def total_credit(self, obj):
        return obj.get_total_credit()
    total_credit.short_description = 'Total Credit'
    
    def is_balanced(self, obj):
        if obj.is_balanced():
            return format_html('<span style="color: green;">✓ Balanced</span>')
        else:
            return format_html('<span style="color: red;">✗ Not Balanced</span>')
    is_balanced.short_description = 'Balanced'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        if obj.status == 'POSTED' and not obj.posted_by:
            obj.posted_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(JournalLine)
class JournalLineAdmin(admin.ModelAdmin):
    list_display = ['journal', 'account', 'debit', 'credit', 'currency', 'exchange_rate', 'description']
    list_filter = ['journal__source_module', 'account__type', 'currency']
    search_fields = ['journal__reference_no', 'account__name', 'description']
    ordering = ['-journal__date', 'account__code']
    
    fieldsets = (
        ('Line Information', {
            'fields': ('journal', 'account', 'debit', 'credit', 'currency', 'exchange_rate', 'description')
        }),
        ('Base Currency Amounts', {
            'fields': ('base_debit', 'base_credit'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['base_debit', 'base_credit']


@admin.register(JournalApproval)
class JournalApprovalAdmin(admin.ModelAdmin):
    list_display = ['journal', 'action', 'actor', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['journal__reference_no', 'actor__username', 'actor__first_name', 'actor__last_name']
    ordering = ['-created_at']


@admin.register(JournalComment)
class JournalCommentAdmin(admin.ModelAdmin):
    list_display = ['journal', 'author', 'is_system', 'created_at']
    list_filter = ['is_system', 'created_at']
    search_fields = ['journal__reference_no', 'author__username', 'author__first_name', 'author__last_name', 'comment']
    ordering = ['-created_at']


@admin.register(LedgerBalance)
class LedgerBalanceAdmin(admin.ModelAdmin):
    list_display = ['account', 'currency', 'opening_balance', 'total_debit', 'total_credit', 
                   'closing_balance', 'last_updated']
    list_filter = ['account__type', 'currency', 'last_updated']
    search_fields = ['account__code', 'account__name']
    ordering = ['account__code']
    readonly_fields = ['closing_balance', 'base_closing_balance', 'last_updated']
    
    fieldsets = (
        ('Account', {
            'fields': ('account', 'currency')
        }),
        ('Account Currency Balances', {
            'fields': ('opening_balance', 'total_debit', 'total_credit', 'closing_balance')
        }),
        ('Base Currency Balances', {
            'fields': ('base_opening_balance', 'base_total_debit', 'base_total_credit', 'base_closing_balance'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PettyCashFund)
class PettyCashFundAdmin(admin.ModelAdmin):
    list_display = ['name', 'custodian', 'account', 'max_amount', 'current_balance', 
                   'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'custodian__first_name', 'custodian__last_name']
    ordering = ['name']
    
    fieldsets = (
        ('Fund Information', {
            'fields': ('name', 'account', 'custodian', 'max_amount')
        }),
        ('Status', {
            'fields': ('is_active', 'current_balance')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['current_balance', 'created_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PettyCashVoucher)
class PettyCashVoucherAdmin(admin.ModelAdmin):
    list_display = ['voucher_no', 'fund', 'date', 'amount', 'description', 
                   'requested_by', 'status', 'approved_by']
    list_filter = ['status', 'fund', 'date']
    search_fields = ['voucher_no', 'description', 'requested_by__first_name', 
                   'requested_by__last_name']
    ordering = ['-date', '-created_at']
    
    fieldsets = (
        ('Voucher Information', {
            'fields': ('voucher_no', 'fund', 'date', 'amount', 'description', 'account')
        }),
        ('Approval', {
            'fields': ('status', 'requested_by', 'approved_by', 'approved_at')
        }),
        ('Payment', {
            'fields': ('paid_at',)
        }),
        ('Audit', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['voucher_no', 'created_at', 'approved_at', 'paid_at']
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.status in ['APPROVED', 'PAID']:
            readonly.extend(['fund', 'amount', 'description', 'account'])
        return readonly


@admin.register(PettyCashReconciliation)
class PettyCashReconciliationAdmin(admin.ModelAdmin):
    list_display = ['fund', 'reconciliation_date', 'physical_cash', 'book_balance', 
                   'difference', 'reconciled_by']
    list_filter = ['fund', 'reconciliation_date']
    search_fields = ['fund__name', 'notes']
    ordering = ['-reconciliation_date']
    
    fieldsets = (
        ('Reconciliation Information', {
            'fields': ('fund', 'reconciliation_date', 'physical_cash', 'book_balance')
        }),
        ('Results', {
            'fields': ('difference', 'notes')
        }),
        ('Audit', {
            'fields': ('reconciled_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['difference', 'created_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set reconciled_by for new objects
            obj.reconciled_by = request.user
        super().save_model(request, obj, form, change)