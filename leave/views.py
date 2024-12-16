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
            staff_category = form.cleaned_data.get('staff_cat')
            academic_year = form.cleaned_data.get('academic_year')
            
            if LeaveEntitlement.objects.filter(staff_cat_id=staff_category, academic_year=academic_year).exists():
                messages.error(request, 'Leave entitlement already exists for the selected staff category and academic year.')
            else:
                form.save()
                return HttpResponseRedirect('leave_entitlement?submitted=True')
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
            staff_category = form.cleaned_data.get('staff_cat')
            academic_year = form.cleaned_data.get('academic_year')

            # Check if another leave entitlement with the same staff category and academic year exists
            if LeaveEntitlement.objects.filter(staff_cat_id=staff_category, academic_year=academic_year).exclude(pk=le_id).exists():
                messages.error(request, 'Leave entitlement already exists for the selected staff category and academic year.')
            else:
                # Save the changes if no conflict
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
            # Check if the academic year already exists
            academic_year = form.cleaned_data.get('academic_year')
            if AcademicYear.objects.filter(academic_year=academic_year).exists():
                messages.error(request, 'Academic year already exists.')
                return redirect('leave-academic-year')
            else:
                form.save()
                return HttpResponseRedirect('leave_academic_year?submitted=True')
    else:
        form = AcademicYearForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form, 'academic_years':academic_years, 'academic_year_count':academic_year_count, 'submitted':submitted}
    print(context)
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


####### Leave Form ############
def request_leave(request):
    submitted = False
    staff_list = Employee.objects.all()
    academic_years = AcademicYear.objects.all()
    staffcategories = StaffCategory.objects.all()

    if request.method == 'POST':
        form = LeaveTransactionForm(request.POST)
        if form.is_valid():
            # Get the input staffno and staff category from the form
            staffno = form.cleaned_data['staffno']
            staff_cat = form.cleaned_data['staff_cat']

            # Fetch the staff object based on the staffno provided in the form
            staff = Employee.objects.filter(pk=staffno).first()

            # If staff does not exist, show an error message
            if not staff:
                messages.error(request, 'Staff number not found. Please check the staff number.')
                return redirect('request-leave')

            # Fetch the company info for the provided staff
            company_info = CompanyInformation.objects.filter(staffno=staff).first()

            # If staff category does not match company info, show an error
            if not company_info or company_info.staff_cat != staff_cat:
                messages.error(request, 'Staff category does not match the staff number.')
                return redirect('request-leave')

            # Get the leave entitlement for the staff category
            leave_entitlement = LeaveEntitlement.objects.filter(staff_cat=staff_cat).first()

            if not leave_entitlement:
                messages.error(request, f'No leave entitlement found for staff category {staff_cat}.')
                return redirect('request-leave')

            # Calculate the remaining leave days
            remaining_days = leave_entitlement.get_remaining_days(staff)

            # Get the number of days requested and academic year
            days_taken = int(form.cleaned_data['days_taken'])
            academic_year = form.cleaned_data['academic_year']

            # Validate if the requested days are within the remaining entitlement
            if remaining_days >= days_taken:
                # Create the leave transaction object
                leave_request = form.save(commit=False)
                leave_request.staffno = staff
                leave_request.staff_cat_id = staff_cat
                leave_request.academic_year = academic_year
                leave_request.save()  # Save the leave request
                messages.success(request, f'Leave request for {days_taken} days submitted successfully.')
                return redirect('request-leave')
            else:
                messages.error(request, f'Not enough leave entitlement remaining for {staff.full_name}.')
        else:
            # If the form is invalid, print errors for debugging (optional)
            print(form.errors)

    else:
        # If the request is a GET, initialize an empty form
        form = LeaveTransactionForm()
        if 'submitted' in request.GET:
            submitted = True

    # Render the leave request page
    return render(request, 'leave/request_leave.html', {
        'form': form,
        'academic_years': academic_years,
        'staff_list': staff_list,
        'submitted': submitted,
        'LEAVE_TYPE': ChoicesLeaveType.objects.all().values_list("name", "name"),
        'staffcategories':staffcategories
    })
    

####### General Request Leave Form ############
def get_staff_details(request, staffno):
    # Fetching staff info using the provided staffno
    staff = Employee.objects.filter(staffno=staffno).first()
    company_info = CompanyInformation.objects.filter(staffno=staffno).first()
    
    if not staff or not company_info:
        return JsonResponse({'error': 'Staff details not found.'}, status=404)
    
    # Safely get the category name
    staff_category = company_info.staff_cat.category_name if company_info.staff_cat else 'No Category'
    
    # Fetching leave entitlement and remaining days
    leave_entitlement = LeaveEntitlement.objects.filter(staff_cat=company_info.staff_cat).first()
    remaining_days = leave_entitlement.get_remaining_days(staff) if leave_entitlement else 0
    
    return JsonResponse({
        'staff_cat': staff_category,
        'remaining_days': remaining_days,
        'staffno': staffno,
    })


def general_leave_request(request):
    if request.method == 'POST':
        form = LeaveTransactionForm(request.POST)
        if form.is_valid():
            staffno = form.cleaned_data['staffno']
            staff_info = get_staff_details(request, staffno)
            
            # Validate staff info
            if 'error' in staff_info:
                messages.error(request, staff_info['error'])
                return redirect('leave-request-form')
            
            # Extract staff details
            remaining_days = int(staff_info.get(remaining_days))
            staff_category = CompanyInformation.objects.get(staffno=staffno).staff_cat  # Get object
            
            days_taken = int(form.cleaned_data['days_taken'])
            academic_year = form.cleaned_data['academic_year']
            
            print(f"StaffData: {staffno}", f"{remaining_days}", f"{staff_category}", f"{days_taken}", f"{academic_year}")
            
            # Check leave entitlement
            if remaining_days < days_taken:
                messages.error(request, 'Not enough leave entitlement remaining.')
                return redirect('leave-request-form')
            
            # Save leave transaction
            leave_transaction = form.save(commit=False)
            leave_transaction.staffno = staffno
            leave_transaction.staff_cat = staff_category  # Assign the object
            leave_transaction.academic_year = academic_year
            leave_transaction.save()
            
            messages.success(request, 'Leave request submitted successfully.')
            return redirect('leave-report')
        else:
            messages.error(request, 'Form is invalid. Please fix the errors.')
    else:
        form = LeaveTransactionForm()

    return render(request, 'leave/general_leave_form.html', {
        'form': form,
        'LEAVE_TYPE': ChoicesLeaveType.objects.all().values_list("name", "name"),
        'academic_years': AcademicYear.objects.all(),
    })



# def general_leave_request(request):
#     submitted = False

#     if request.method == 'POST':
#         form = LeaveTransactionForm(request.POST)

#         if form.is_valid():
#             staffno = form.cleaned_data['staffno']
#             print(f"Staff number received: {staffno}")  # Debugging: print the staffno

#             # Get staff info after form is valid and staffno is available
#             staff_info = get_staff_details(request, staffno)

#             # if 'error' in staff_info:  # If the response contains an error
#             #     messages.error(request, staff_info['error'])
#             #     return redirect('leave-request-form')  # Or the relevant page
            
#             staffno_data = staff_info.get('staffno')  # Get staffno from staff_info dictionary
#             remaining_days = staff_info.get('remaining_days')  # Get remaining_days from staff_info
#             staff_category = staff_info.get('staff_cat')  # Get staff_cat from staff_info

#             print(f"Staff info received: {staffno_data}")
#             print(f"Remaining days: {remaining_days}")
#             print(f"Staff category: {staff_category}")
            
#             # staffno_data = staff_info['staffno']
#             # staffno_data = staff_info.get('staffno')  # Get staffno from staff_info dictionary
#             # remaining_days = staff_info.get('remaining_days', 0)  # Get remaining_days from staff_info
#             # staff_category = staff_info.get('staff_cat', 'No Category')  # Get staff_cat from staff_info

#             # remaining_days = staff_info['remaining_days']
#             # staff_category = staff_info['staff_cat']

#             # Get the other fields from the form
#             days_taken = int(form.cleaned_data['days_taken'])
#             academic_year = form.cleaned_data['academic_year']
            
#             print(f"Days taken: {days_taken}")
#             print(f"Academic year: {academic_year}")
            
#             leave_transaction = form.save(commit=False)
#             leave_transaction.staffno = staffno_data
#             leave_transaction.staff_cat_id = staff_category  # Assuming it's a staff category object

#             # Check if there are enough leave days available
#             if remaining_days >= days_taken:
#                 # Create or update leave transaction
#                 leave_transaction.academic_year = academic_year
#                 leave_transaction.save()

#                 messages.success(request, 'Leave request submitted successfully.')
#                 return redirect('leave-report')
#             else:
#                 messages.error(request, 'Not enough leave entitlement remaining.')

#         else:
#             messages.error(request, 'Please fix the form errors and try again.')

#     else:
#         form = LeaveTransactionForm()
#         if 'submitted' in request.GET:
#             submitted = True

#     # Render the form with the necessary context data
#     return render(request, 'leave/general_leave_form.html', {
#         'form': form,
#         'LEAVE_TYPE': ChoicesLeaveType.objects.all().values_list("name", "name"),
#         'academic_years': AcademicYear.objects.all(),
#     })

