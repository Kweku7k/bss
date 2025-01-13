from django.shortcuts import render
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
import pprint
from .models import *
from hr.models import *
from .forms import *
from hr.forms import *
from setup.models import *
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.http import JsonResponse



# Create your views here.
def medical_entitlement(request):
    submitted = False
    staffcategorys = StaffCategory.objects.all()
    academic_years = AcademicYear.objects.all()
    medical_entitlements = MedicalEntitlement.objects.all()
    medical_entitlement_count = medical_entitlements.count()
    if request.method == 'POST':
        form = MedicalEntitlementForm(request.POST)
        if form.is_valid():
            # Check if the medical entitlement already exists
            staff_category = form.cleaned_data.get('staff_cat')
            academic_year = form.cleaned_data.get('academic_year')
            
            if MedicalEntitlement.objects.filter(staff_cat=staff_category, academic_year=academic_year).exists():
                messages.error(request, 'Medical entitlement already exists for the selected staff category and academic year.')
            else:
                form.save()
                messages.success(request, 'Medical entitlement added successfully.')
                return HttpResponseRedirect('medical_entitlement?submitted=True')
    else:
        form = MedicalEntitlementForm()
        if 'submitted' in request.GET:
            submitted = True
    context = {
        'form':form, 
        'medical_entitlements':medical_entitlements, 
        'medical_entitlement_count':medical_entitlement_count,
        'staffcategorys': staffcategorys,
        'academic_years': academic_years,
        'submitted':submitted,
    }
    return render(request, 'medical/medical_entitlement.html', context)


def edit_medical_entitlement(request, me_id):
    medical_entitlements = MedicalEntitlement.objects.order_by('-id')
    medical_entitlement_count = medical_entitlements.count()
    medical_ent = MedicalEntitlement.objects.get(pk=me_id)
    academic_years = AcademicYear.objects.all()
    staffcategorys = StaffCategory.objects.order_by('category_abbr') 
    form = MedicalEntitlementForm(instance=medical_ent)
    
    if request.method == 'POST':
        form = MedicalEntitlementForm(request.POST, instance=medical_ent)
        if form.is_valid():
            staff_category = form.cleaned_data.get('staff_cat')
            academic_year = form.cleaned_data.get('academic_year')

            # Check if another medical entitlement with the same staff category and academic year exists
            if MedicalEntitlement.objects.filter(staff_cat=staff_category, academic_year=academic_year).exclude(pk=me_id).exists():
                messages.error(request, 'Medical entitlement already exists for the selected staff category and academic year.')
            else:
                # Save the changes if no conflict
                form.save()
                return redirect('medical-entitlement')
    context = {'form':form, 'medical_entitlements':medical_entitlements, 'medical_entitlement_count':medical_entitlement_count, 'staffcategorys':staffcategorys, 'medical_ent':medical_ent, 'academic_years':academic_years}
    return render(request, 'medical/medical_entitlement.html', context)


def delete_medical_entitlement(request, me_id):
    medical_entitlement = MedicalEntitlement.objects.get(pk=me_id)
    if request.method == 'GET':
        medical_entitlement.delete()
    return redirect('medical-entitlement')


############## Mediacl Report ###################
def medical_report(request):
    staff_categories = StaffCategory.objects.all()
    academic_years = AcademicYear.objects.all()
    medical_transactions = Medical.objects.all()
    hospitals = Hospital.objects.all()
    
    filter_staffcategory = request.GET.get('filter_staffcategory')
    selected_academic_year = request.GET.get('academic_year')
    filter_by_hospital = request.GET.get('filter_by_hospital')
    filter_by_month = request.GET.get('filter_by_month') 


    # Apply filters based on user input
    if filter_staffcategory:
        medical_transactions = medical_transactions.filter(staff_cat=filter_staffcategory)
    
    if selected_academic_year:
        medical_transactions = medical_transactions.filter(academic_year=selected_academic_year)
    
    if filter_by_hospital:
        medical_transactions = medical_transactions.filter(hospital_code=filter_by_hospital)
        
    # Apply month filter if provided
    if filter_by_month:
        try:
            # Ensure filter_by_month is a valid integer for month (1-12)
            filter_by_month = int(filter_by_month)
            medical_transactions = medical_transactions.filter(date_attended__month=filter_by_month)
        except ValueError:
            # If not a valid month, you could set an error or handle gracefully
            medical_transactions = medical_transactions.none()


    context = {
        'medical_transactions': medical_transactions,
        'staff_categories': staff_categories,
        'filter_staffcategory': filter_staffcategory,
        'selected_academic_year': selected_academic_year,
        'academic_years': academic_years,
        'filter_by_hospital': filter_by_hospital,
        'hospitals': hospitals,
        'filter_by_month': filter_by_month,
    }
    
    pprint.pprint(context)
    
    return render(request, 'medical/medical_report.html', context)
