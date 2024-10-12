from datetime import date
from django.shortcuts import render, redirect
import pprint
from .models import Leave
from .models import *
from hr.models import *
from .forms import *
from setup.models import *
from django.http import HttpResponseRedirect


############ LEAVE REQUEST ##################

def leave_request(request):
    context = {}
    return render(request, 'leave/leave_request.html', context)


############ Leave Entitlement ##################


def leave_entitlement(request):
    submitted = False
    leave_entitlements = LeaveEntitlement.objects.all()
    leave_entitlement_count = leave_entitlements.count()
    academic_years = AcademicYear.objects.all()
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
    context = {'form':form, 'leave_entitlements':leave_entitlements, 'leave_entitlement_count':leave_entitlement_count, 'submitted':submitted, 'staffcategorys':staffcategorys, 'academic_years':academic_years}
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
    academic_years = AcademicYear.objects.all()
    staffcategorys = StaffCategory.objects.order_by('category_abbr') 
    form = LeaveEntitlementForm(instance=leave_ent)
    
    if request.method == 'POST':
        form = LeaveEntitlementForm(request.POST, instance=leave_ent)
        if form.is_valid():
            form.save()
            return redirect('leave-entitlement')
    context = {'form':form, 'leave_entitlements':leave_entitlements, 'leave_entitlement_count':leave_entitlement_count, 'staffcategorys':staffcategorys, 'leave_ent':leave_ent, 'academic_years':academic_years}
    return render(request, 'leave/leave_entitlement.html', context)


############ Academic Year ##################
def leave_academic_year(request):
    submitted = False
    academic_years = AcademicYear.objects.all()
    academic_year_count = academic_years.count()
    if request.method == "POST":
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('leave_academic_year')
    else:
        form = AcademicYearForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form, 'academic_years':academic_years, 'academic_year_count':academic_year_count, 'submitted':submitted}
    return render(request, 'leave/academic_year.html', context)

def edit_leave_academic_year(request, ay_id):
    academic_years = AcademicYear.objects.order_by('-id')
    academic_year_count = academic_years.count()
    academic_year = AcademicYear.objects.get(pk=ay_id)
    form = AcademicYearForm(instance=academic_year)

    if request.method == 'POST':
        form = AcademicYearForm(request.POST, instance=academic_year)
        if form.is_valid():
            form.save()
            return redirect('leave-academic-year')
    context = {'form':form, 'academic_years':academic_years, 'academic_year_count':academic_year_count, 'academic_year':academic_year}
    return render(request, 'leave/academic_year.html', context)


def delete_leave_academic_year(request, ay_id):
    academic_year = AcademicYear.objects.get(pk=ay_id)
    if request.method == 'GET':
        academic_year.delete()
    return redirect('leave-academic-year')



############## Leave Report ###################
def leave_report(request):
    staff_categories = StaffCategory.objects.all()
    academic_years = AcademicYear.objects.all()
    leave_transactions = Staff_Leave.objects.all()
    
    filter_staffcategory = request.GET.get('filter_staffcategory')
    selected_academic_year = request.GET.get('academic_year')

    # Apply filters based on user input
    if filter_staffcategory:
        leave_transactions = leave_transactions.filter(staff_cat=filter_staffcategory)
    
    if selected_academic_year:
        leave_transactions = leave_transactions.filter(academic_year=selected_academic_year)
        
    try:
        filter_staffcategory_body = StaffCategory.objects.get(pk=filter_staffcategory).category_name
    except StaffCategory.DoesNotExist:
        filter_staffcategory_body = None

    context = {
        'leave_transactions': leave_transactions,
        'staff_categories': staff_categories,
        'filter_staffcategory': filter_staffcategory,
        'filter_staffcategory_body': filter_staffcategory_body,
        'selected_academic_year': selected_academic_year,
        'academic_years': academic_years,
    }
    
    pprint.pprint(context)
    
    return render(request, 'leave/leave_report.html', context)