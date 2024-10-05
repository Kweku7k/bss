from datetime import date
from django.shortcuts import render, redirect 
from .models import Leave
from .models import *
from hr.models import *
from .forms import *
from setup.models import *
from django.http import HttpResponseRedirect


############ LEAVE RWQUEST ##################

def leave_request(request):
    context = {}
    return render(request, 'leave/leave_request.html', context)

def leave_entitlement(request):
    submitted = False
    leave_entitlements = LeaveEntitlement.objects.all()
    leave_entitlement_count = leave_entitlements.count()
    staffcategorys = StaffCategory.objects.order_by('category_abbr') 
    if request.method == "POST":
        form = LeaveEntitlementForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('leave_entitlement')
    else:
        form = LeaveEntitlementForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form, 'leave_entitlements':leave_entitlements, 'leave_entitlement_count':leave_entitlement_count, 'submitted':submitted, 'staffcategorys':staffcategorys}
    return render(request, 'leave/leave_entitlement.html', context)
    
    
def delete_leave_entitlement(request, le_id):
    leave_entitlement = LeaveEntitlement.objects.get(pk=le_id)
    if request.method == 'GET':
        leave_entitlement.delete()
    return redirect('leave-entitlement')

def edit_leave_entitlement(request, le_id):
    leave_entitlements = LeaveEntitlement.objects.order_by('-id')
    leave_entitlement_count = leave_entitlements.count()
    leave_ent = LeaveEntitlement.objects.get(pk=le_id)
    staffcategorys = StaffCategory.objects.order_by('category_abbr') 
    form = LeaveEntitlementForm(instance=leave_ent)
    
    if request.method == 'POST':
        form = LeaveEntitlementForm(request.POST, instance=leave_ent)
        if form.is_valid():
            form.save()
            return redirect('leave-entitlement')
    context = {'form':form, 'leave_entitlements':leave_entitlements, 'leave_entitlement_count':leave_entitlement_count, 'staffcategorys':staffcategorys, 'leave_ent':leave_ent}
    return render(request, 'leave/leave_entitlement.html', context)


# Leave report view
def leave_report(request):
    # Get all staff categories for dropdown selection
    staff_categories = StaffCategory.objects.all()
    
    # Retrieve filter values from request
    filter_staffcategory = request.GET.get('filter_staffcategory')
    selected_academic_year = request.GET.get('academic_year')
    
    # Get all leave transactions
    leave_transactions = Staff_Leave.objects.all()

    # Apply filters based on user input
    if filter_staffcategory:
        leave_transactions = leave_transactions.filter(staff_cat__id=filter_staffcategory)
    
    if selected_academic_year:
        leave_transactions = leave_transactions.filter(academic_year=selected_academic_year)

    # Render the filtered leave transactions and staff categories to the template
    context = {
        'leave_transactions': leave_transactions,
        'staff_categories': staff_categories,
        'filter_staffcategory': filter_staffcategory,
        'selected_academic_year': selected_academic_year,
    }
    
    return render(request, 'leave/leave_report.html', context)