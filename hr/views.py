from decimal import Decimal, InvalidOperation
import json
from math import e
import pprint
import uuid
from django.http import HttpResponseRedirect, JsonResponse, FileResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse

from hr.payroll_helper import PayrollCalculator # type: ignore
from .models import *
from django.contrib.auth.models import Group, User, Permission
from setup.models import *
from leave.models import *
from medical.models import *
from django.db.models import Q
from .forms import *
from collections import defaultdict
from django.db import connection # type: ignore
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import csv
from django.db import transaction
from django.utils import timezone
import logging
from datetime import datetime, timedelta
import os
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator
from hr.decorators import role_required, tag_required
from django.db.models.functions import Concat
from django.db.models import F, Value, CharField, Sum, Max, Count
from datetime import date
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from hr.utils.export import render_to_excel, render_to_pdf
from bss.firebase import upload_file_to_firebase, delete_file_from_firebase
import tempfile



logger = logging.getLogger('activity')

def parse_date(date_str):
    if not date_str:
        return None 
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected format is YYYY-MM-DD.")


def to_bool(val):
    return str(val).strip().lower() in ['true', '1', 'yes']


def handler404(request, exception):
    return render(request, '404.html', status=404)

@login_required
def view_logs(request):
    log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.environ.get('LOG_FILE', 'activity.log'))
    logs = []

    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as f:
            for line in f.readlines():
                parts = line.strip().split(' ', 3)
                if len(parts) == 4:
                    date = parts[0]
                    time = parts[1]
                    level = parts[2]
                    message = parts[3]
                    logs.append({
                        'datetime': f"{date} {time}",
                        'level': level,
                        'message': message,
                    })
    return render(request, 'hr/logs.html', {'logs': logs})


def register(request):
    form = RegistrationForm()
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            print("Someone is creating an account", form.cleaned_data)
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            if User.objects.filter(email=email).exists():
                messages.error(request, "Oops, Email address already exists. Please use another email.")
                return redirect('register')
            form.save()
            messages.success(request, f"Account Creation for {username} has been successful")  
            logger.info(f"Account Creation for {username} has been successful")
            return redirect('login')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{error}")
            print(form.errors)
            return redirect('register')
    
    context = {'form': form}
    print(context)
    return render(request, 'authentication/register.html', context)

def waiting_approval(request):
    return render(request, 'authentication/waiting_approval.html')

def index(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user_username = User.objects.get(email=email)
            user = authenticate(request, username=user_username.username, password=password)
            print("Trying to Login", user)
            if user is not None:
                # Check if the user is not approve and redirect
                if not user.approval and not user.is_superuser:
                    logger.warning(f"Login attempt by unapproved user: {user.username}")
                    messages.error(request, "Your account is not approved yet. Please contact the administrator.")
                    return redirect('waiting_approval')
                login(request, user)
                messages.success(request, f"Login Successful. Welcome Back {user.username}")
                logger.info(f"Login Successful: {user.username}")
                return redirect('landing')
            else:
                messages.error(request, "Invalid login credentials.")
                return redirect('login')
        except User.DoesNotExist:
            messages.error(request, "Email not found.")
            return redirect('login')

    return render(request, 'authentication/login.html', {})

def user_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f"Profile Updated Successful for {username}")
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)

    context = {'form': form}
    print(context)
    return render(request, 'hr/profile.html', context)  

def user_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'hr/password.html', {'form': form})


def logoutUser(request):
    username = request.user.username
    logger.info(f"Logout Successful: {username}")
    logout(request)
    return redirect('login')
    

@login_required(login_url='login')
def landing(request):
    staffs = Employee.objects.exclude(companyinformation__active_status='Inactive').order_by('lname')
    company_info = CompanyInformation.objects.all()
    active = CompanyInformation.objects.filter(active_status__exact='Active')
    inactive = CompanyInformation.objects.filter(active_status__exact='Inactive')
    dormant = CompanyInformation.objects.filter(active_status__exact='Dormant')
    staff_count = staffs.count()
    ative_count = active.count()
    inactive_count = inactive.count()
    dormant_count = dormant.count()
    
    today = timezone.now().date()
    expiring_soon = company_info.filter(doe__lte=today + timedelta(days=180)).order_by('doe')
    sixty_and_above = []
    pending_renewals = RenewalHistorys.objects.filter(is_approved=False, is_disapproved=False)
    pending_promotions = PromotionHistory.objects.filter(is_approved=False, is_disapproved=False)
    pending_users = User.objects.filter(approval=False, is_superuser=False)    
    pending_exits = Exits.objects.filter(is_approved=False, is_disapproved=False)
    pending_updates = PendingEmployeeUpdate.objects.filter(is_approved=False)
    
    
    for staff in staffs:
        company_info = CompanyInformation.objects.filter(staffno=staff).first()
        if not company_info:
            continue 
        
        staff.company_info = company_info

        # retirement_age = 65 if company_info.staff_cat.lower() == "senior member(admin)" else 60
        if company_info.staff_cat and company_info.staff_cat.lower() == "senior member":
            retirement_age = 65
        else:
            retirement_age = 60

        retirement_date = today - timedelta(days=retirement_age * 365)

        if staff.dob <= retirement_date:
            sixty_and_above.append(staff)

            if company_info.ssn_con:
                company_info.ssn_con = False
                company_info.save()
                logger.info(f"Disabled SSN contribution for {staff.fname} {staff.lname} (Retirement Age {retirement_age})")
                
    for staff in sixty_and_above:
        staff_company_info = CompanyInformation.objects.filter(staffno=staff).first()
        
        if staff_company_info:
            staff.company_info = staff_company_info
            
            if staff_company_info.ssn_con:
                staff_company_info.ssn_con = False
                staff_company_info.save()
                logger.info(f"Disabled SSN contribution for {staff.fname} {staff.lname} due to age over 60")  
    
    notification_count = ( expiring_soon.count() + len(sixty_and_above) + pending_renewals.count() + pending_promotions.count() )

    context = {
        'staffs':staffs,
        'company_info':company_info,
        'active':active,
        'inactive':inactive,
        'dormant':dormant,
        'staff_count':staff_count,
        'ative_count':ative_count,
        'inactive_count':inactive_count,
        'dormant_count':dormant_count,
        'expiring_soon':expiring_soon,
        'notification_count':notification_count,
        'pending_renewals':pending_renewals,
        'sixty_and_above':sixty_and_above,
        'pending_promotions':pending_promotions,
        'pending_users':pending_users,
        'pending_exits': pending_exits,
        'pending_updates':pending_updates,
    }
    
    return render(request,'hr/landing_page.html', context)


def topnav_view(request):
    company_info = CompanyInformation.objects.exclude(active_status='Inactive')    
    today = timezone.now().date()
    expiring_soon = company_info.filter(doe__lte=today + timedelta(days=30)).order_by('doe')

    return render(request, 'partials/_topnav.html', {'expiring_soon': expiring_soon, 'company_info':company_info})

def search(request):
    if request.method == 'POST' and 'search' in request.POST:
        staffs = Employee.objects.exclude(companyinformation__active_status='Inactive').order_by('fname')
        company_info = CompanyInformation.objects.all()
        search_query = request.POST.get('search')
        if search_query:
            staffs = staffs.filter(
                Q(staffno__icontains=search_query) |
                Q(fname__icontains=search_query) |
                Q(lname__icontains=search_query) |
                Q(middlenames__icontains=search_query)
            )      

        staff_count = staffs.count()
    
        context = {
            'staffs': staffs,
            'staff_count': staff_count,
            'company_info':company_info,
        }
    
        return render(request, 'hr/search.html', context)
    
    return render(request, 'hr/search.html',{})

def deletestaff(request,staffno):  
    staffpix = ""
    staffs = Employee.objects.order_by('lname').filter(active_status__exact='Active') 
    staff_count = staffs.count()
    # staff = Employee.objects.filter(staffno__exact=staffno) 
    staff = Employee.objects.get(pk=staffno)
    staff1 = staff.title + ' ' + staff.fname 
    if staff.middlenames:
        staff1 +=  ' ' + staff.middlenames
    staff1 += ' ' + staff.lname
    if staff.suffix:
        staff1 +=  ' ' + staff.suffix
    # if staff.staff_pix:
    #     staffpix = "{{ staff.staff_pix }}"
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("UPDATE hr_employee SET active_status = 'Inactive' WHERE staffno = %s", [staffno])
            return render(request,'hr/new_staff.html',{'staff':staff,'staffs':staffs,'staff_count':staff_count})
    return render(request, 'delete.html',{'obj':staff1,'staff':staff})


@login_required
def staff_details(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    schools = School.objects.order_by('school_name')
    try:
        company_info = CompanyInformation.objects.get(staffno=staffno)
    except CompanyInformation.DoesNotExist:
        messages.warning(request, "Company Information not found for this staff.")
        return redirect('edit-company-info', staffno=staffno)  # or any other appropriate view
    # company_info = CompanyInformation.objects.get(staffno=staff)
    return render(request,'hr/staff_data.html',{'staff':staff,'schools':schools, 'company_info':company_info})



@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('edit_staff')
def edit_staff(request, staffno):
    submitted = False
    staffs = Employee.objects.order_by('lname').filter() 
    staff_count = staffs.count()
    title = Title.objects.order_by("title_name")
    staffcategory = StaffCategory.objects.order_by("category_name")
    qualification = Qualification.objects.order_by("qual_abbr")
    staff = Employee.objects.get(pk=staffno)
    form = EmployeeForm(request.POST or None,request.FILES or None,instance=staff)
    
    if request.method == 'POST':
        if form.is_valid():
            print("Edit Information", form.cleaned_data)

            fname = form.cleaned_data['fname']
            lname = form.cleaned_data['lname']

            # Instead of immediately saving:
            staff_instance = form.save(commit=False)

            # 📸 Handle image upload
            image_file = request.FILES.get('staff_pix')

            if image_file:
                try:
                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                        for chunk in image_file.chunks():
                            temp_file.write(chunk)
                        temp_file.flush()

                        unique_filename = f"{uuid.uuid4().hex}_{image_file.name}"
                        firebase_path = f"staff_pictures/{unique_filename}"
                        firebase_url = upload_file_to_firebase(temp_file.name, firebase_path)

                        staff_instance.staff_pix = firebase_url

                except Exception as e:
                    print(f"Error uploading to Firebase: {str(e)}")
                    
            # Now save safely
            staff_instance.save()
            full_name = f"{fname} {lname}"
            messages.success(request, f"Staff data for {full_name} has been updated successfully")
            logger.info(f"Personal information updated for {full_name} by {request.user.username}")
            return redirect('staff-details', staffno)
        
            # else: 
            #     messages.warning(request, "No changes were made to the staff record.")
            # return redirect('staff-details', staffno)
        else:
            print(form.errors)
            messages.error(request, "Form submission failed. Please check the form for errors.")
            logger.error(f"Failed to update staff data for staff #{staffno}. Errors: {form.errors}")
            
    else:
        form = EmployeeForm
        if 'submitted' in request.GET:
            submitted = True   
    context = {
                'form':form,
               'submitted':submitted,
               'staffs':staffs,
               'staff_count':staff_count,
               'RBA':[(q.name, q.name)  for q in ChoicesRBA.objects.all()],
               'STAFFLEVEL':STAFFLEVEL,
               'STAFFSTATUS':[(q.name, q.name)  for q in ChoicesStaffStatus.objects.all()],
               'STAFFRANK':STAFFRANK,
               'GENDER': ChoicesGender.objects.order_by("name").values_list("name", "name"),
               'SUFFIX': ChoicesSuffix.objects.order_by("name").values_list("name", "name"),
               'REGION': ChoicesRegion.objects.order_by("name").values_list("name", "name"),
               'MARITALSTATUS': ChoicesMaritalStatus.objects.order_by("name").values_list("name", "name"),
               'IDTYPE': ChoicesIdType.objects.order_by("name").values_list("name", "name"),
               'DENOMINATION': ChoicesDenomination.objects.order_by("name").values_list("name", "name"),
               'DEPENDANTS':DEPENDANTS,
               'RELIGION': ChoicesReligion.objects.order_by("name").values_list("name", "name"),
               'HPQ': ChoicesHPQ.objects.order_by("name").values_list("name", "name"),
               'title':title,
               'qualification':qualification,
               'staffcategory':staffcategory,
               'staff':staff,
               }

    # context = {'form':form,'staffs':staffs,'staff_count':staff_count,'staff':staff}
    return render(request, 'hr/edit_new_staff.html', context)


# Write a filtering query set for 


@login_required
def allstaff(request): 
    search_query = request.POST.get('search', '')
    status_filter = request.GET.get("status", None)
    filters = Q()

    if search_query:
        filters &= (
            Q(fname__icontains=search_query) | 
            Q(lname__icontains=search_query) | 
            Q(staffno__icontains=search_query) | 
            Q(middlenames__icontains=search_query)
        )
    
    if status_filter:
        filters &= Q(companyinformation__active_status=status_filter)

    # Filtered queryset
    staffs = Employee.objects.filter(filters).exclude(companyinformation__active_status='Inactive').order_by('lname')
    staff_count = staffs.count()
    company_info = CompanyInformation.objects.all()
    
    print("All Staff", staffs)

    # Pagination
    paginator = Paginator(staffs, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'staffs': page_obj,
        'staff_count': staff_count,
        'company_info': company_info,
        'search_query': search_query,
        'STAFFSTATUS': [(q.name, q.name) for q in ChoicesStaffStatus.objects.all()],
    }

    return render(request, 'hr/allstaff.html', context)


@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('dormant_staff')
def dormant_staff(request): 
    staffs = Employee.objects.filter(companyinformation__active_status='Inactive').order_by('lname')
    staff_count = staffs.count()
    company_info = CompanyInformation.objects.all()
    
    print("Dormant Staff", staffs)
        
    # Pagination
    paginator = Paginator(staffs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'staffs': page_obj,
        'staff_count': staff_count,
        'company_info': company_info,
    }

    return render(request, 'hr/dormant_staff.html', context)
  
@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
def report(request): 
    staffs = Employee.objects.exclude(companyinformation__active_status='Inactive').order_by('lname')
    company_info = CompanyInformation.objects.all()
    staff_school = Staff_School.objects.all()
    
    staff_category_custom = [
        ("faculty", "Faculty / Lecturers"),
        ("admin", "Admin")
    ]

    
    AGE_CLASSIFICATIONS = {
        "child": (0, 12),
        "teen": (13, 19), 
        "young_adult": (20, 35),
        "middle_adult": (36, 60),
        "senior_adult": (61, 100),
        "elderly": (101, 300)
    }
    
    AGE_LABELS = {
        "child": "Child (0-12)",
        "teen": "Teen (13-19)",
        "young_adult": "Young Adult (20-35)", 
        "middle_adult": "Middle Aged (36-60)",
        "senior_adult": "Senior Adult (61-100)",
        "elderly": "Elderly (101+)"
    }
    
    # Custom minimum age
    min_age = request.GET.get("min_age")
    max_age = request.GET.get("max_age")
    
    # Initialize filter variables
    filter_staffcategory = None
    filter_qualification = None
    filter_title = None
    filter_contract = None
    filter_status = None
    filter_gender = None
    filter_department = None
    filter_jobtitle = None
    filter_directorate = None
    filter_school_faculty = None
    filter_age = None
    filter_renewal = None
    filter_promotion = None
    filter_category = None

    # Initial filter container
    filters = Q()

    if request.method == 'POST':
        # Retrieve filter values from POST request - getlist for multiple values
        filter_staffcategory = request.POST.getlist('filter_staffcategory')
        filter_qualification = request.POST.getlist('filter_qualification') 
        filter_title = request.POST.getlist('filter_title')
        filter_contract = request.POST.getlist('filter_contract')
        filter_status = request.POST.getlist('filter_status')
        filter_gender = request.POST.getlist('filter_gender')
        filter_department = request.POST.getlist('filter_department')
        filter_jobtitle = request.POST.getlist('filter_jobtitle')
        filter_directorate = request.POST.getlist('filter_directorate')
        filter_school_faculty = request.POST.getlist('filter_school_faculty')
        filter_age = request.POST.get('filter_age')
        filter_renewal = request.POST.get('filter_renewal')
        filter_promotion = request.POST.get('filter_promotion')
        filter_category = request.POST.get('filter_category')

        # Filter by Staff Category
        if filter_staffcategory:
            filters &= Q(companyinformation__staff_cat__in=filter_staffcategory)

        # Filter by Contract Type
        if filter_contract:
            filters &= Q(companyinformation__contract__in=filter_contract)

        # Filter by Qualification
        if filter_qualification:
            qualification_filter = Q(heq__in=filter_qualification) | Q(staff_school__certification__in=filter_qualification)
            filters &= qualification_filter

        # Filter by Title
        if filter_title:
            filters &= Q(title__in=filter_title)

        # Filter by Gender
        if filter_gender:
            filters &= Q(gender__in=filter_gender)

        # Filter by Status
        if filter_status:
            company_info = CompanyInformation.objects.filter(active_status__in=filter_status)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)

        # Filter by Department
        if filter_department:
            company_info = CompanyInformation.objects.filter(dept__in=filter_department)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)
            
            
        # Filter by Category
        if filter_category == "faculty":
            faculty_ids = CompanyInformation.objects.exclude(sch_fac_dir__isnull=True).exclude(sch_fac_dir="").values_list('staffno_id', flat=True)
            filters &= Q(staffno__in=faculty_ids)

        elif filter_category == "admin":
            admin_ids = CompanyInformation.objects.exclude(directorate__isnull=True).exclude(directorate="").values_list('staffno_id', flat=True)
            filters &= Q(staffno__in=admin_ids)

        # Filter by Job Title  
        if filter_jobtitle:
            company_info = CompanyInformation.objects.filter(job_title__in=filter_jobtitle)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)  
                      
        # Filter by Directorate
        if filter_directorate:
            company_info = CompanyInformation.objects.filter(directorate__in=filter_directorate)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)
            
        # Filter by School/Faculty
        if filter_school_faculty:
            company_info = CompanyInformation.objects.filter(sch_fac_dir__in=filter_school_faculty)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)
                
        # ✅ Prioritize Custom Age first
        if filter_age == "custom" and min_age and max_age:
            try:
                min_age = int(min_age)
                max_age = int(max_age)

                if 0 <= min_age <= 999 and 0 <= max_age <= 999:
                    current_date = date.today()
                    start_date = current_date - timedelta(days=max_age * 365)
                    end_date = current_date - timedelta(days=min_age * 365)
                    filters &= Q(dob__range=(start_date, end_date))
            except ValueError:
                pass  # Ignore invalid inputs

        # ✅ If no custom age is used, apply predefined filters
        elif filter_age and filter_age in AGE_CLASSIFICATIONS:
            age_range = AGE_CLASSIFICATIONS[filter_age]
            current_date = date.today()
            start_date = current_date - timedelta(days=age_range[1] * 365)
            end_date = current_date - timedelta(days=age_range[0] * 365)
            filters &= Q(dob__range=(start_date, end_date))
                
        # Filter by Renewal History
        if filter_renewal == "true":
            renewal_staffno = {renewal.staffno_id for renewal in RenewalHistorys.objects.filter(is_approved=True, is_disapproved=False)}
            filters &= Q(staffno__in=renewal_staffno)
            
        # Filter by Promotion History
        if filter_promotion == "true":
            promotion_staffno = {promotion.staffno_id for promotion in PromotionHistory.objects.filter(is_approved=True, is_disapproved=False)}
            filters &= Q(staffno__in=promotion_staffno)

        # Apply filters to the staff queryset
        staffs = staffs.filter(filters).distinct()  # Ensure distinct entries
        
        print("Queries for staff", staffs)

    # Pagination setup
    paginator = Paginator(staffs, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Gather context data
    context = {
        'staffs': page_obj,
        'staff_school': staff_school,
        'staff_count': staffs.count(),  # Use the filtered count
        'staffcategory': [(q.category_name, q.category_name) for q in StaffCategory.objects.all()],
        'company_info': company_info,
        'qualification': [(q.qual_abbr, q.qual_abbr) for q in Qualification.objects.all()],
        'title': [(q.title_abbr, q.title_abbr) for q in Title.objects.all()],
        'contract': [(q.contract_type, q.contract_type) for q in Contract.objects.all()],
        'STAFFSTATUS': [(q.name, q.name) for q in ChoicesStaffStatus.objects.all()],
        'GENDER': [(q.name, q.name) for q in ChoicesGender.objects.all()],
        'department': [(q.dept_long_name, q.dept_long_name) for q in Department.objects.all()],
        'jobtitle': [(q.job_title, q.job_title) for q in JobTitle.objects.all()],
        'directorate': [(q.direct_name, q.direct_name) for q in Directorate.objects.all()],
        'school_faculty': [(q.sch_fac_name, q.sch_fac_name) for q in School_Faculty.objects.all()],
        'age_classifications': AGE_LABELS,
        'staff_category_custom': staff_category_custom,
        # The filters being used for rendering in the template 
        'filter_staffcategory': filter_staffcategory,
        'filter_qualification': filter_qualification,
        'filter_title': filter_title,
        'filter_contract': filter_contract,
        'filter_status': filter_status,
        'filter_gender': filter_gender,
        'filter_department': filter_department,
        'filter_jobtitle': filter_jobtitle,
        'filter_directorate': filter_directorate,
        'filter_school_faculty': filter_school_faculty,
        'filter_category': filter_category,
        'filter_age': filter_age,
        'min_age': min_age,
        'max_age': max_age,
        'filter_renewal': filter_renewal,
        'filter_promotion': filter_promotion,
        'renewal_staffno': {renewal.staffno_id for renewal in RenewalHistorys.objects.all()},
    }

    return render(request, 'hr/report.html', context)


@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('add_staff')
def newstaff(request):
    submitted = False
    staffs = Employee.objects.order_by('lname').filter()
    title = Title.objects.all()
    qualification = Qualification.objects.order_by('qual_abbr')
    staffcategory = StaffCategory.objects.order_by('category_name')
    staff_count = staffs.count()
    
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            print("New Staff Info", form.cleaned_data)
            
            staff_number = form.cleaned_data['staffno']
            fname = form.cleaned_data['fname']
            lname = form.cleaned_data['lname']

            # Check if staffno already exists
            if Employee.objects.filter(staffno=staff_number).exists():
                full_name = f"{fname} {lname}"
                messages.error(request, f"Staff number {staff_number} for {full_name} already exists. Please use another unique staff number.")
                print(f"Staff number {staff_number} already exists")
            else:
                print("Form was submitted successfully", form.cleaned_data)
                staff_instance = form.save(commit=False)

                image_file = request.FILES.get('staff_pix')
                if image_file:
                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                        for chunk in image_file.chunks():
                            temp_file.write(chunk)
                        temp_file.flush()
                        firebase_path = f"staff_pictures/{image_file.name}"
                        firebase_url = upload_file_to_firebase(temp_file.name, firebase_path)
                        staff_instance.staff_pix = firebase_url 

                # Save staff to DB
                staff_instance.save()
                url = reverse('company-info', kwargs={'staffno': str(staff_number)})
                full_name = f"{fname} {lname}"
                messages.success(request, f"The details for staff member {full_name} have been successfully created in the system")
                logger.info(f"New staff created: {full_name} by {request.user.username}")
                print(url)
                return HttpResponseRedirect(url)
        else:
            print(form.errors)
            messages.error(request, "Form submission failed. Please check the form for errors.")
    else:
        form = EmployeeForm
        if 'submitted' in request.GET:
            submitted = True
    context = {
            'form':form,
            'submitted':submitted,
            'staffs':staffs,
            'staff_count':staff_count,
            'RBA':[(q.name, q.name) for q in ChoicesRBA.objects.order_by('name')],
            'STAFFLEVEL': ChoicesStaffLevel.objects.order_by('name').values_list("name", "name"),
            'STAFFSTATUS':[(q.name, q.name) for q in ChoicesStaffStatus.objects.order_by('name')],
            'GENDER': ChoicesGender.objects.order_by('name').values_list("name", "name"), 
            'DEPENDANTS':[(q.name, q.name) for q in ChoicesDependants.objects.order_by('name')],
            'qualification':qualification,
            'HPQ':[(q.name, q.name) for q in ChoicesHPQ.objects.order_by('name')],
            'REGION':[(q.name, q.name) for q in ChoicesRegion.objects.order_by('name')],
            'title':title,
            'staffcategory':staffcategory,
            'qualification':qualification,
            'MARITALSTATUS': ChoicesMaritalStatus.objects.order_by('name').values_list("name", "name"),
            'IDTYPE': ChoicesIdType.objects.order_by('name').values_list("name", "name"),
            'DENOMINATION': ChoicesDenomination.objects.order_by('name').values_list("name", "name"),
            'RELIGION': ChoicesReligion.objects.order_by('name').values_list("name", "name"),
            'SUFFIX':[(q.name, q.name) for q in ChoicesSuffix.objects.order_by('name')]            
        }
    return render(request,'hr/new_staff.html',context)


def get_bank_branches(request, bank_name):
    try:
        bank = Bank.objects.get(bank_short_name=bank_name)  # Find bank by name
        branches = BankBranch.objects.filter(bank_code=bank)  # Get branches associated with this bank
        branch_data = [{"branch_name": branch.branch_name} for branch in branches]
        print("Branch Data", branch_data)
        return JsonResponse({"branches": branch_data})
    except Bank.DoesNotExist:
        return JsonResponse({"branches": []}, status=404)


def get_departments(request, sch_name):
    try:
        school_faculty = School_Faculty.objects.get(sch_fac_name=sch_name)  
        departments = Department.objects.filter(sch_fac=school_faculty) # Get departments associated with this school/faculty
        department_data = [{"dept_long_name": dept.dept_long_name} for dept in departments]
        print("Department Data", department_data)
        return JsonResponse({"departments": department_data})
    except School_Faculty.DoesNotExist:
        return JsonResponse({"departments": []}, status=404)
    

def get_units_by_directorate(request, directorate_name):
    try:
        directorate = Directorate.objects.get(direct_name=directorate_name)
        units = Unit.objects.filter(directorate=directorate)
        unit_data = [{"unit_name": unit.unit_name} for unit in units]
        print(unit_data)
        return JsonResponse({"units": unit_data})
    except Directorate.DoesNotExist:
        return JsonResponse({"units": []}, status=404)
    
def get_units_by_department(request, dept_name):
    try:
        department = Department.objects.get(dept_long_name=dept_name)
        units = Unit.objects.filter(department=department)
        unit_data = [{"unit_name": unit.unit_name} for unit in units]
        return JsonResponse({"units": unit_data})
    except Department.DoesNotExist:
        return JsonResponse({"units": []}, status=404)

    
@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('add_staff')
def company_info(request,staffno):
    submitted = False
    company_infos = CompanyInformation.objects.filter(staffno__exact=staffno)    
    staff = Employee.objects.get(pk=staffno)
    staffcategory = StaffCategory.objects.order_by('category_name')
    contract = Contract.objects.order_by('contract_type')
    campus = Campus.objects.order_by('campus_name')
    school_faculty = School_Faculty.objects.order_by('sch_fac_name')
    directorate = Directorate.objects.order_by('direct_name')
    bank_list = Bank.objects.order_by('bank_short_name')
    bankbranches = BankBranch.objects.order_by('branch_name')
    departments = Department.objects.order_by('dept_long_name')
    ranks = JobTitle.objects.order_by('job_title')
    jobtitle = StaffRank.objects.order_by('staff_rank')
    units = Unit.objects.order_by('unit_name')
    salary_scales = SalaryScale.objects.order_by("name")
    
    
    if request.method == 'POST':
        form = CompanyInformationForm(request.POST, request.FILES)
        if form.is_valid(): 
            print("Company Info", form.cleaned_data)
            
            ssn_con = form.cleaned_data.get('ssn_con')
            pf_con = form.cleaned_data.get('pf_con')
            company_info = form.save(commit=False)
            company_info.staffno = staff 
            company_info.ssn_con = ssn_con
            company_info.pf_con = pf_con
            company_info.save()
            staff_number = staff.pk  
            url = reverse('emp-relation', kwargs={'staffno': str(staff_number)})
            print(url)
            full_name = f"{staff.fname} {staff.lname}"
            messages.success(request, f"Company information created for {full_name}")
            logger.info(f"Company information created for {full_name} by {request.user.username}")
            return HttpResponseRedirect(url)
        else:
            print("form.errors")
            print(form.errors)
    else:
        form = CompanyInformationForm
        if 'submitted' in request.GET:
            submitted = True
    context = {
        'form':form,
        'submitted':submitted,
        'company_infos':company_infos,
        'staff':staff,
        'staffcategory':staffcategory,
        'campus':campus,
        'bank_list':bank_list,
        'contract':contract,
        'bankbranches':bankbranches,
        'school_faculty':school_faculty,
        'directorate':directorate,
        'RBA':[(q.name, q.name)  for q in ChoicesRBA.objects.order_by("name")],
        'STAFFLEVEL': ChoicesStaffLevel.objects.order_by("name").values_list("name", "name"),
        'STAFFSTATUS':[(q.name, q.name)  for q in ChoicesStaffStatus.objects.order_by("name")],
        'DEPENDANTS':[(q.name, q.name)  for q in ChoicesDependants.objects.order_by("name")],
        'departments':departments,
        'jobtitle':jobtitle,
        'ranks':ranks,
        'units':units,
        'salary_scales':salary_scales,
        'COSTCENTERS': departments.values_list('dept_long_name', 'dept_long_name').union(directorate.values_list('direct_name', 'direct_name')),
    }
    return render(request,'hr/company_info.html',context)

@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('edit_staff')
def edit_company_info(request,staffno):
    company_infos = CompanyInformation.objects.all()  
    staff = Employee.objects.get(pk=staffno)
    company_info, created = CompanyInformation.objects.get_or_create(staffno=staff)
    company_info_count = company_infos.count()
    
    staffcategory = StaffCategory.objects.order_by('category_name')
    contract = Contract.objects.order_by('contract_type')
    campus = Campus.objects.order_by('campus_name')
    school_faculty = School_Faculty.objects.order_by('sch_fac_name')
    directorate = Directorate.objects.order_by('direct_name')
    bank_list = Bank.objects.order_by('bank_short_name')
    bankbranches = BankBranch.objects.order_by('branch_name')
    departments = Department.objects.order_by('dept_long_name')
    ranks = JobTitle.objects.order_by('job_title')
    jobtitle = StaffRank.objects.order_by('staff_rank')
    units = Unit.objects.order_by('unit_name')
    salary_scales = SalaryScale.objects.order_by("name")
    
    if created:
        messages.info(request, f"No previous company info found. A new record has been prepared for {staff.fname}.")

    
    if request.method == 'POST':
        form = CompanyInformationForm(request.POST, request.FILES, instance=company_info)
        if form.is_valid():
            print("Edit Company Info", form.cleaned_data)

            if form.has_changed():
                print("Edit Company Info", form.cleaned_data)
                
                form.save()
                full_name = f"{staff.fname} {staff.lname}"
                messages.success(request, f"Company information for {full_name} has been updated successfully")
                logger.info(f"Company information updated for {full_name} by {request.user.username}")
            else:
                messages.warning(request, "No changes were made to the company information.")
            return redirect('staff-details', staffno=staffno)
        else:
            print("form.errors")
            print(form.errors)
    else:
        form = CompanyInformationForm(instance=company_info)
        
    context = {
                'form':form,
            #    'submitted':submitted,
               'RBA':RBA,
               'STAFFLEVEL':STAFFLEVEL,
               'STAFFSTATUS':[(q.name, q.name)  for q in ChoicesStaffStatus.objects.order_by("name")],
               'GENDER': ChoicesGender.objects.order_by("name").values_list("name", "name"),
               'SUFFIX': ChoicesSuffix.objects.order_by("name").values_list("name", "name"),
               'REGION': ChoicesRegion.objects.order_by("name").values_list("name", "name"),
               'DEPENDANTS':DEPENDANTS,
               'HPQ':[(q.name, q.name)  for q in ChoicesHPQ.objects.order_by("name")],               
               'staffcategory':staffcategory,
               'company_info':company_info,
               'company_infos':company_infos,
               'staff':staff,
               'contract':contract,
               'company_info_count':company_info_count,
               'campus':campus,
               'school_faculty':school_faculty,
               'directorate':directorate,
               'departments':departments,
               'bank_list': bank_list,
                'bank_branches': bankbranches,
                'jobtitle':jobtitle,
                'ranks':ranks,
                'salary_scales':salary_scales,
                'units':units,
                'COSTCENTERS': departments.values_list('dept_long_name', 'dept_long_name').union(directorate.values_list('direct_name', 'direct_name')),
            }

    return render(request, 'hr/company_info.html', context)

############### EMPLOYEE RELATIONSHIP ###############

def verify_user(request):
    days = range(1, 32)
    years = range(1950, 2026)
    
    if request.method == "POST":
        staffno = request.POST.get("staffno").strip()
        day = request.POST.get("dob_day").strip()
        month = request.POST.get("dob_month").strip()
        year = request.POST.get("dob_year").strip()

        dob = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        try:
            employee = Employee.objects.get(staffno=staffno, dob=dob)
            
            pending, created = PendingEmployeeUpdate.objects.get_or_create(
                staffno=employee,
                defaults={
                    "title": employee.title,
                    "lname": employee.lname,
                    "fname": employee.fname,
                    "middlenames": employee.middlenames,
                    "gender": employee.gender,
                    "dob": employee.dob,
                    "staff_pix": employee.staff_pix,
                }
            )
            
            print("Pending Employee", pending.staffno)

            return redirect('submit-personal-info', staffno=staffno, dob=dob)
        except Employee.DoesNotExist:
            return render(request, "hr/verification_failed.html", {"staffno": staffno})

    context = {
        "days": days,
        "years": years,
    }
    return render(request, "hr/verify_user.html", context)


def verify_complete(request):
    return render(request, "hr/update_success.html")

def submit_personal_info(request, staffno, dob):
    submitted = False
    title = Title.objects.all()
    qualification = Qualification.objects.all()
    employee = get_object_or_404(Employee, staffno=staffno, dob=dob)

    
    try:
        pending = get_object_or_404(PendingEmployeeUpdate, staffno=employee)
    except PendingEmployeeUpdate.DoesNotExist:
        messages.error(request, "No pending record found for the provided details. Please verify your information again.")
        return redirect("verify-user")
    
    form = PendingEmployeeUpdateForm(request.POST or None, request.FILES or None, instance=pending)

    if request.method == 'POST':
        if form.is_valid():
            print("Staff Updating Information", form.cleaned_data)
            fname = form.cleaned_data['fname']
            lname = form.cleaned_data['lname']
            staff_instance = form.save(commit=False)
            # staff_instance.staffno = employee 
            
            # 📸 Handle image upload
            image_file = request.FILES.get('staff_pix')

            if image_file:
                try:
                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                        for chunk in image_file.chunks():
                            temp_file.write(chunk)
                        temp_file.flush()

                        unique_filename = f"{uuid.uuid4().hex}_{image_file.name}"
                        firebase_path = f"staff_pictures/{unique_filename}"
                        firebase_url = upload_file_to_firebase(temp_file.name, firebase_path)

                        staff_instance.staff_pix = firebase_url

                except Exception as e:
                    print(f"Error uploading to Firebase: {str(e)}")
            
            staff_instance.save()
            full_name = f"{fname} {lname}"
            logger.info(f"{full_name} has updated their Personal Information")
            return redirect('verify-complete')
        else:
            plain_error_message = " | ".join(
                error for errors in form.errors.values() for error in errors)
            messages.error(request, f"Please correct the errors below: {plain_error_message}")
            # messages.error(request, f"Please correct the errors below.{form.errors}")
            print(form.errors)
    else:
        form = PendingEmployeeUpdateForm
        if 'submitted' in request.GET:
            submitted = True
            
            
    context = {
        'form':form,
        "staff": pending,
        "submitted": submitted,
        'RBA':[(q.name, q.name)  for q in ChoicesRBA.objects.all()],
        'STAFFLEVEL':STAFFLEVEL,
        'STAFFSTATUS':[(q.name, q.name)  for q in ChoicesStaffStatus.objects.all()],
        'STAFFRANK':STAFFRANK,
        'GENDER': ChoicesGender.objects.all().values_list("name", "name"),
        'SUFFIX': ChoicesSuffix.objects.all().values_list("name", "name"),
        'REGION': ChoicesRegion.objects.all().values_list("name", "name"),
        'MARITALSTATUS': ChoicesMaritalStatus.objects.all().values_list("name", "name"),
        'IDTYPE': ChoicesIdType.objects.all().values_list("name", "name"),
        'DENOMINATION': ChoicesDenomination.objects.all().values_list("name", "name"),
        'DEPENDANTS':DEPENDANTS,
        'RELIGION': ChoicesReligion.objects.all().values_list("name", "name"),
        'HPQ': ChoicesHPQ.objects.all().values_list("name", "name"),
        'title':title,
        'qualification':qualification,
    }
            
    return render(request, "hr/personal_info_form.html", context)




@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('view_pending_update')
def view_pending_update(request, staffno):
    employee = get_object_or_404(Employee, staffno=staffno)
    pending_update = get_object_or_404(PendingEmployeeUpdate, staffno=employee)

    context = {
        'employee': employee,
        'pending': pending_update
    }
    return render(request, 'hr/review_pending_update.html', context)
    


@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
def approve_pending_update(request, update_id):
    pending_update = get_object_or_404(PendingEmployeeUpdate, id=update_id)

    if request.method == 'POST':
        employee = pending_update.staffno  

        fields_to_copy = [
            'title', 'fname', 'lname', 'middlenames', 'oname', 'suffix', 'gender', 'dob',
            'nationality', 'ethnic', 'home_town', 'm_status', 'region', 'pob','religion','denomination','email_address','active_phone','ssnitno','idtype','gcardno','digital',
            'residential','postal','blood','car','chassis', 'vech_type','study_area','heq','completion_year','institution','other_heq','hpq','staff_pix'
        ]

        for field in fields_to_copy:
            setattr(employee, field, getattr(pending_update, field))

        employee.save()

        pending_update.delete()

        messages.success(request, f"Update for {employee.fname} {employee.lname} has been approved and updated.")
        logger.info(f"Pending update for {employee.staffno} approved by {request.user.username}.")

        return redirect('staff-details', staffno=employee.staffno)

    return redirect('landing')



@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
def disapprove_pending_update(request, update_id):
    pending_update = get_object_or_404(PendingEmployeeUpdate, id=update_id)

    if request.method == 'POST':
        full_name = f"{pending_update.fname} {pending_update.lname}"
        pending_update.delete()

        messages.warning(request, f"Pending update for {full_name} has been disapproved and removed.")
        logger.info(f"Pending update for {full_name} disapproved by {request.user.username}.")

        return redirect('landing')

    return redirect('landing')


    

@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('add_staff')
def emp_relation(request,staffno):
    submitted = False
    emp_relations = Kith.objects.filter(staffno__exact=staffno)
    emp_count = emp_relations.count()
    staff = Employee.objects.get(pk=staffno)
    
    if request.method == 'POST':
        form = KithForm(request.POST)
        if form.is_valid():
            print("Employee Relation", form.cleaned_data) 
            new_percentage = form.cleaned_data['percentage']
            current_total = sum(emp.percentage for emp in emp_relations)
            
            kin = form.cleaned_data.get('kin')
            ben = form.cleaned_data.get('ben')
            
            if current_total + new_percentage > 100:
                messages.error(request, 'Total percentage exceeds 100%. Please adjust the percentage.')
            else:
                emp_relation = form.save(commit=False)
                emp_relation.staffno = staff
                emp_relation.kin = kin
                emp_relation.ben = ben
                emp_relation.save()
                full_name = f"{staff.fname} {staff.lname}"
                messages.success(request, f"Beneficiaries for {full_name} has been created successfully")
                logger.info(f"Beneficiaries added for {full_name} by {request.user.username}")
                return redirect('emp-relation', staffno)
            
        else:
            print("form.errors")
            print(form.errors)
    else:
        form = KithForm
        if 'submitted' in request.GET:
            submitted = True
    context = {
        'form':form,
        'submitted':submitted,
        'emp_relations':emp_relations,
        'emp_count':emp_count,
        'staff':staff,
        'RELATIONSHIP': ChoicesDependants.objects.order_by("name").values_list("name", "name"),
        'STATUS': ChoicesRelationStatus.objects.order_by("name").values_list("name", "name"),
        'GENDER': ChoicesGender.objects.order_by("name").values_list("name", "name"),
        'total_percentage': sum(emp.percentage for emp in emp_relations),
    }
    return render(request,'hr/emp_relation.html',context)

@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('edit_staff')
def edit_emp_relation(request,staffno,emp_id):
    emp_relations = Kith.objects.filter(staffno__exact=staffno)  
    emp_relation = Kith.objects.get(pk=emp_id)
    staff = Employee.objects.get(pk=staffno)
    emp_count = emp_relations.count()
    form = KithForm(request.POST or None,instance=emp_relation)

    if request.method == 'POST':
        form = KithForm(request.POST, instance=emp_relation)
        if form.is_valid():
            print("Employee Relation", form.cleaned_data)
            
            kin = form.cleaned_data.get('kin')
            ben = form.cleaned_data.get('ben')
            
            if form.has_changed():
                form.save()
                emp_relation = form.save(commit=False)
                emp_relation.staffno = staff
                emp_relation.kin = kin
                emp_relation.ben = ben
                emp_relation.save()
                
                full_name = f"{staff.fname} {staff.lname}"
                messages.success(request, f"Employee Beneficiaries for {full_name} has been updated successfully")
                logger.info(f"Employee Beneficiaries updated for {full_name} by {request.user.username}")
            return redirect('emp-relation', staffno=staffno)
        
        print("form.errors", form.errors)
    context = {
        'form':form,
        'emp_relations':emp_relations,
        'emp_relation':emp_relation,
        'staff':staff,
        'emp_count':emp_count,
        'RELATIONSHIP': ChoicesDependants.objects.order_by("name").values_list("name", "name"),
        'STATUS': ChoicesRelationStatus.objects.order_by("name").values_list("name", "name"),
        'GENDER': ChoicesGender.objects.order_by("name").values_list("name", "name"),
    }

    return render(request, 'hr/emp_relation.html', context)

@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('delete_staff')
def delete_emp_relation(request,emp_id,staffno):
    emp_relation = Kith.objects.get(pk=emp_id)
    staff = Employee.objects.get(pk=staffno)
    if request.method == 'GET':
       emp_relation.delete()
       messages.success(request, ("Beneficiary deleted successfully"))
       logger.info(f"Beneficiary deleted for {staff.fname} by {request.user.username}")
       
    return redirect('emp-relation', staffno)

# END OF EMPLOYEE RELATIONSHIP 



# Write a function for bulk upload csv format
@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('bulk_upload')
def bulk_upload(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']

            # Check file extension
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'This is not a CSV file.')
                return render(request, 'hr/upload.html', {'form': form})

            # Read and parse the CSV file
            try:
                decoded_file = csv_file.read().decode('utf-8')
                reader = csv.DictReader(decoded_file.splitlines())  
                errors = []  # To store errors
                success_count = 0  # Count successful uploads
                duplicates = []  # To store duplicate entries

                # Using transaction.atomic to ensure all-or-nothing
                with transaction.atomic():
                    for row in reader:
                        savepoint = transaction.savepoint()

                        try:
                            # Process Employee CSV data
                            employee, created = Employee.objects.get_or_create(
                                staffno=row['staffno'],
                                defaults={  # Only set these fields if it's a new entry
                                    'title': row['title'],
                                    'lname': row['lname'],
                                    'fname': row['fname'],
                                    'middlenames': row.get('middlenames', ''),
                                    'oname': row.get('oname', ''),
                                    'suffix': row.get('suffix', ''),
                                    'gender': row.get('gender', ''),
                                    'dob': parse_date(row.get('dob', '')),
                                    'm_status': row.get('m_status', ''),
                                    'nationality': row.get('nationality', ''),
                                    'ethnic': row.get('ethnic', ''),
                                    'home_town': row.get('home_town', ''),
                                    'region': row.get('region', ''),
                                    'pob': row.get('pob', ''),
                                    'religion': row.get('religion', ''),
                                    'denomination': row.get('denomination', ''),
                                    'email_address': row.get('email_address', ''),
                                    'active_phone': row.get('active_phone', ''),
                                    'ssnitno': row.get('ssnitno', ''),
                                    'idtype': row.get('idtype', ''),
                                    'gcardno': row.get('gcardno', ''),
                                    'digital': row.get('digital', ''),
                                    'residential': row.get('residential', ''),
                                    'postal': row.get('postal', ''),
                                    'blood': row.get('blood', ''),
                                    'car': row.get('car', ''),
                                    'chassis': row.get('chassis', ''),
                                    'vech_type': row.get('vech_type', ''),
                                    'study_area': row.get('study_area', ''),
                                    'heq': row.get('heq', ''),
                                    'completion_year': row.get('completion_year', ''),
                                    'institution': row.get('institution', ''),
                                    'hpq': row.get('hpq', ''),
                                    'created': timezone.now(),
                                }
                            )
                            
                            print(f"Uploading data for {employee.fname} {employee.lname} {employee.staffno} ")
                            
                            # If employee already exists, add to duplicates and skip
                            if not created:
                                duplicates.append(f"{row['fname']} {row['lname']}")
                                transaction.savepoint_rollback(savepoint)
                                continue
                            
                            # Continue processing if it's a new employee
                            # Handle Bank instance
                            bank_short_name = row.get('bank_name')
                            bank_instance = None
                            if bank_short_name:
                                bank_instance, created = Bank.objects.get_or_create(bank_short_name=bank_short_name)
                            
                            # Handle BankBranch instance
                            branch_name = row.get('bank_branch')
                            branch_instance = None
                            if branch_name and bank_instance:
                                branch_instance, created = BankBranch.objects.get_or_create(branch_name=branch_name, bank_code=bank_instance)
                            
                            # Handle Staff Category instance
                            category_name = row.get('staff_cat')
                            staff_category_instance = None
                            if category_name:
                                staff_category_instance, created = StaffCategory.objects.get_or_create(category_name=category_name)
                            
                            # Handle Contract instance
                            contract_type = row.get('contract')
                            contract_instance = None
                            if contract_type:
                                contract_instance, created = Contract.objects.get_or_create(contract_type=contract_type)
                            
                            # Handle School/Faculty instance
                            sch_fac_name = row.get('sch_fac_dir')
                            sch_fac_instance = None
                            if sch_fac_name:
                                sch_fac_instance, created = School_Faculty.objects.get_or_create(sch_fac_name=sch_fac_name)
                            
                            # Process Directorate if available
                            direct_name = row.get('directorate')
                            direct_instance = None
                            if direct_name:
                                direct_instance, created = Directorate.objects.get_or_create(direct_name=direct_name)
                            
                            # Handle Department instance
                            dept_long_name = row.get('dept')
                            dept_long_instance = None
                            if dept_long_name:
                                dept_long_instance, created = Department.objects.get_or_create(dept_long_name=dept_long_name, sch_fac=sch_fac_instance)
                                
                            
                            # Handle Department Unit instance
                            unit_name = row.get('dept_unit')
                            dept_unit_instance = None
                            if unit_name:
                                dept_unit_instance, created = Unit.objects.get_or_create(unit_name=unit_name, department=dept_long_instance)
                            
                            
                            # Handle Directorate Unit instance
                            unit_name = row.get('directorate_unit')
                            direct_unit_instance = None
                            if unit_name:
                                direct_unit_instance, created = Unit.objects.get_or_create(unit_name=unit_name, directorate=direct_instance)
                            
                            
                            print("Starting Company Info")
                            # Process CompanyInformation data if present in CSV
                            company_info, created = CompanyInformation.objects.get_or_create(
                                staffno=employee,  # linking to the employee instance
                                defaults={
                                    'job_title': row.get('job_title', ''),
                                    'job_description': row.get('job_description', ''),
                                    'staff_cat': staff_category_instance,
                                    'contract': contract_instance,
                                    'active_status': row.get('active_status', ''),
                                    'doa': parse_date(row.get('doa', None)),
                                    'doe': parse_date(row.get('doe', None)),
                                    'renewal': parse_date(row.get('renewal', None)), 
                                    'rank': row.get('rank', ''),
                                    'campus': row.get('campus', ''),
                                    'city': row.get('city', ''),
                                    'email': row.get('email', ''),
                                    'sch_fac_dir': sch_fac_instance,
                                    'directorate': direct_instance,
                                    'dept': dept_long_instance,
                                    'dept_unit': dept_unit_instance,
                                    'directorate_unit': direct_unit_instance,
                                    'salary': row.get('salary', ''),
                                    'cost_center': dept_long_instance,
                                    'bank_name': bank_instance,
                                    'bank_branch': branch_instance, 
                                    'accno': row.get('accno', ''),
                                    'ssn_con': to_bool(row.get('ssn_con', '')),
                                    'pf_con': to_bool(row.get('pf_con', '')),
                                    'acc_name': row.get('acc_name', ''),
                                    'probation': parse_date(row.get('probation', None)),
                                    'pte': row.get('pte', ''),
                                    'basic_entitled_percentage': row.get('basic_entitled_percentage') or "100.00",
                                }
                            )
                            print("Company Info Done for ", company_info.staffno)
                            # print(f"Company Information: {company_info}")
                            success_count += 1
                        except Exception as row_error:
                            transaction.savepoint_rollback(savepoint)
                            errors.append(f"Error in row {reader.line_num}: {row_error}")
                            # print(f"Error in row {reader.line_num}, column: {', '.join(row_error.args)}")     
                            print(f"Error in row {reader.line_num}, column: {', '.join(str(arg) for arg in row_error.args)}")
                                                   
                            continue
                        finally:
                            transaction.savepoint_commit(savepoint)

                # Report success and any errors
                if success_count:
                    messages.success(request, f'Successfully uploaded {success_count} records.')
                    logger.info(f"Successfully uploaded {success_count} records by {request.user.username}")
                
                if duplicates:
                    if len(duplicates) > 3:
                        duplicate_message = f"{', '.join(duplicates[:3])} and {len(duplicates)-3} more"
                    else:
                        duplicate_message = ', '.join(duplicates)
                    messages.warning(request, f'Skipped {len(duplicates)} duplicate entries including: {duplicate_message}')
                
                if errors:
                    error_message = "</p><p>".join(errors)
                    messages.error(request, f"Errors occurred during upload:\n{error_message}")
            except Exception as e:
                messages.error(request, f"Error processing file: {e}")
        
    else:
        form = CSVUploadForm()

    return render(request, 'hr/upload.html', {'form': form})


def download_csv(request):
    file_path = os.path.join(settings.MEDIA_ROOT, 'docs/sample_format.csv')
    response = FileResponse(open(file_path, 'rb'), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_format.csv"'
    return response


####### EDUCATIONAL BACKGROUND #################
@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('add_staff')
def education(request,staffno):
    submitted = False
    educations = Staff_School.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    qualification = Qualification.objects.all()
    school = School.objects.all()
    school_list = School.objects.order_by('school_name')

    
    if request.method == 'POST':
        form = StaffSchoolForm(request.POST)
        if form.is_valid(): 
            print("Educational Background", form.cleaned_data)
            education = form.save(commit=False)
            education.staffno = staff
            education.save()
            full_name = f"{staff.fname} {staff.lname}"
            messages.success(request, f"Educational Background for {full_name} has been created successfully")
            logger.info(f"Educational Background for {full_name} has been created successfully by {request.user.username}")
            return redirect('education', staffno)
    else:
        form = StaffSchoolForm
        if 'submitted' in request.GET:
            submitted = True
    context = {
               'form':form,
               'submitted':submitted,
               'educations':educations,
               'staff':staff,
               'qualification':qualification,
               'school':school,
               'school_list':school_list,
            }
    return render(request,'hr/education.html',context)


@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('edit_staff')
def edit_education(request,staffno,edu_id):
    educations = Staff_School.objects.filter(staffno__exact=staffno)  
    education = Staff_School.objects.get(pk=edu_id)
    staff = Employee.objects.get(pk=staffno)
    edu_count = educations.count()
    school = School.objects.all()
    qualification = Qualification.objects.all() 
    school_list = School.objects.order_by('school_name')
    form = StaffSchoolForm(request.POST or None,instance=education)
    

    if request.method == 'POST':
        form = StaffSchoolForm(request.POST, instance=education)
        if form.is_valid():
            if form.has_changed():
                form.save()
                full_name = f"{staff.fname} {staff.lname}"
                messages.success(request, f"Educational Background for {full_name} has been updated successfully")
                logger.info(f"Educational Background updated for {full_name} by {request.user.username}")            
            return redirect('education', staffno=staffno)
        
    context = {
                'form':form,
                'educations':educations,
                'education':education,
                'staff':staff,
                'edu_count':edu_count,
                'qualification':qualification,
                'school':school,
                'school_list':school_list,
                'RELATIONSHIP': ChoicesDependants.objects.all().values_list("name", "name"),
               'STATUS': ChoicesRelationStatus.objects.all().values_list("name", "name"),
                'GENDER': ChoicesGender.objects.all().values_list("name", "name"),
               }

    return render(request, 'hr/education.html', context)



@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('delete_staff')
def delete_education(request,edu_id,staffno):
    education = Staff_School.objects.get(pk=edu_id)
    staff = Employee.objects.get(pk=staffno)
    if request.method == 'GET':
        full_name = f"{staff.fname} {staff.lname}"
        messages.success(request, f"Educational Background for {full_name} has been deleted successfully")
        logger.info(f"Educational Background deleted for {full_name} by {request.user.username}")
        education.delete()
    return redirect('education', staffno)


######################################################################
### Staff leave transaction
######################################################################
@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('record_leave')
def leave_transaction(request, staffno):
    submitted = False
    staff = get_object_or_404(Employee, pk=staffno) 
    company_info = get_object_or_404(CompanyInformation, staffno=staff)   
    leave_entitlement = LeaveEntitlement.objects.filter(staff_cat=company_info.staff_cat).first()
    leave_transactions = Staff_Leave.objects.filter(staffno__exact=staffno)
    # fetch already taken leave dates and send them to the template
    taken_dates = Staff_Leave.objects.filter(staffno__exact=staffno).values_list('start_date', 'end_date')
    leave_trans_count = leave_transactions.count()
    academic_years = AcademicYear.objects.all()

    if not leave_entitlement:
        messages.error(request, 'No leave entitlement found for this staff category.')
        return redirect('leave-entitlement')

    remaining_days = leave_entitlement.get_remaining_days(staff)
    staff_fullname = f"{staff.title} {staff.fname} {staff.lname}"

    if request.method == 'POST':
        print("Form submitted")
        form = LeaveTransactionForm(request.POST)
        if form.is_valid():
            leave_type = ChoicesLeaveType.objects.get(name=form.cleaned_data['leave_type'])
            days_taken = int(form.cleaned_data['days_taken'])
            academic_year = form.cleaned_data['academic_year']
            
            leave_transaction = form.save(commit=False)
            leave_transaction.staffno = staff
            leave_transaction.staff_cat = request.POST.get('staff_cat')
            
            if leave_type.deductible:
                if remaining_days >= days_taken:
                    leave_transaction.academic_year = academic_year
                    leave_transaction.save()
                    
                    messages.success(request, f'Leave transaction created successfully for {staff_fullname}.')
                    logger.info(f'Leave transaction created successfully for {staff_fullname} by {request.user.username}')
                    return redirect('leave-transaction', staffno=staffno)
                else:
                    messages.error(request, 'Insufficient leave balance to process this request. Please review the leave days entered')
            else:
                leave_transaction.academic_year = academic_year
                leave_transaction.save()
                
                messages.success(request, f'Leave transaction created successfully for {staff_fullname}. (Non-deductible leave)')
                logger.info(f'Leave transaction created successfully for {staff_fullname} by {request.user.username} (Non-deductible leave)')
                return redirect('leave-transaction', staffno=staffno)
        else:
            print(form.errors)
            messages.error(request, 'Form is not valid. Please check the entered data.')
            return redirect('leave-transaction', staffno=staffno)
    else:
        form = LeaveTransactionForm()
        if 'submitted' in request.GET:
            submitted = True
    print(taken_dates)
    return render(request, 'hr/leave.html', {
        'staff': staff,
        'staff_cat': company_info.staff_cat,
        'leave_entitlement': leave_entitlement,
        'leave_transactions': leave_transactions,
        'form': form,
        'submitted': submitted,
        'company_info': company_info,
        'LEAVE_TYPE': ChoicesLeaveType.objects.all().values_list("name", "name"),
        'leave_trans_count':leave_trans_count,
        'remaining_days': remaining_days,
        'academic_years': academic_years,
        'taken_dates': taken_dates,
    })
    
    
@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('modify_leave')
def edit_leave_transaction(request, staffno, lt_id):
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = get_object_or_404(CompanyInformation, staffno=staff)
    academic_years = AcademicYear.objects.all()
    leave_transactions = Staff_Leave.objects.filter(staffno__exact=staffno)
    leave_transaction = get_object_or_404(Staff_Leave, pk=lt_id)
    leave_entitlement = LeaveEntitlement.objects.filter(staff_cat=company_info.staff_cat).first()
    
    # Calculate the remaining leave days
    remaining_days = leave_entitlement.get_remaining_days(staff)
    remaining_days += leave_transaction.days_taken
    form = LeaveTransactionForm(request.POST or None, instance=leave_transaction)
    staff_fullname = f"{staff.title} {staff.fname} {staff.lname}"
    if request.method == 'POST':
        if form.is_valid():
            days_taken = int(form.cleaned_data['days_taken'])
            
            if remaining_days >= days_taken:
                if form.has_changed():
                    form.save()
                    messages.success(request, f'Leave transaction updated successfully for {staff_fullname}.')
                    logger.info(f'Leave transaction updated successfully for {staff_fullname} by {request.user.username}')
                return redirect('leave-transaction', staffno=staffno)
            else:
                messages.error(request, 'Insufficient leave balance to process this request. Please review the leave days entered')
    
    context = {
        'staff': staff,
        'staff_cat': company_info.staff_cat,
        'leave_transactions': leave_transactions,
        'leave_transaction': leave_transaction,
        'form': form,
        'company_info': company_info,
        'LEAVE_TYPE': ChoicesLeaveType.objects.all().values_list("name", "name"),
        'academic_years': academic_years,
        'leave_entitlement': leave_entitlement,
        'remaining_days': remaining_days,  # Pass remaining days to the template
    }

    return render(request, 'hr/leave.html', context)



######################################################################
### Staff Medical views
######################################################################

@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('record_medical_bill')
def medical_transaction(request, staffno):
    submitted = False
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = get_object_or_404(CompanyInformation, staffno=staff)
    academic_years = AcademicYear.objects.all()
    hospitals = Hospital.objects.all()
    medical_transactions = Medical.objects.filter(staffno=staff)
    medical_trans_count = medical_transactions.count()

    # Get active academic year
    active_year = AcademicYear.objects.filter(active=True).first()
    active_year_value = active_year.academic_year if active_year else None

    # Get all entitlements for this staff category in the active year
    entitlements = MedicalEntitlement.objects.filter(
        staff_cat=company_info.staff_cat,
        academic_year=active_year_value
    )
    
    if not entitlements.exists():
        messages.error(request, f"No medical entitlement set for {company_info.staff_cat} in {active_year_value}.")
        return redirect('medical-entitlement')

    # Build entitlement summary for OPD, Admission, Surgery    
    treatment_summary = []
    for treatment in ChoicesMedicalTreatment.objects.all():
        ttype = treatment.name
        ent = entitlements.filter(treatment_type=ttype).first()
        if ent:
            used = ent.get_amount_used(staff)
            remaining = ent.get_remaining_amount(staff)
            surcharge = ent.get_surcharge(staff)
            treatment_summary.append({
                'type': ttype,
                'entitlement': ent.entitlement,
                'used': used,
                'remaining': remaining,
                'surcharge': surcharge
            })

    # Load beneficiaries
    bene_list = Kith.objects.filter(staffno=staff).annotate(
        full_name=Concat(
            F('kith_fname'), Value(' '),
            F('kith_middlenames'), Value(' '),
            F('kith_lname'),
            output_field=CharField()
        )
    ).values_list('full_name', 'full_name')
    staff_fullname = f"{staff.title} {staff.fname} {staff.lname}"
    final_bene_list = [(staff.staffno, staff_fullname)] + list(bene_list)

    if request.method == 'POST':
        form = MedicalTransactionForm(request.POST)
        if form.is_valid():
            treatment_type = form.cleaned_data['nature']
            academic_year = form.cleaned_data['academic_year']
            selected_key = form.cleaned_data['patient_name']
            bene_dict = dict(final_bene_list)
            patient_name = bene_dict.get(selected_key, selected_key)  # fallback if not found

            # Get the correct entitlement
            medical_entitlement = entitlements.filter(treatment_type=treatment_type).first()


            if not medical_entitlement:
                messages.error(request, f"No entitlement for {treatment_type} in {academic_year}.")
                return redirect('medical-transaction', staffno=staffno)
            
            # Accept all transactions regardless of balance (surcharge will be shown later)
            medical_transaction = form.save(commit=False)
            medical_transaction.staffno = staff
            medical_transaction.patient_name = patient_name
            medical_transaction.staff_cat = company_info.staff_cat
            medical_transaction.save()

            messages.success(request, f'Medical transaction created for {staff_fullname}.')
            return redirect('medical-transaction', staffno=staffno)
        else:
            print("There was an error")
            print(form.errors)
            messages.error(request, 'Form is not valid.')
    else:
        form = MedicalTransactionForm()
        if 'submitted' in request.GET:
            submitted = True

    context = {
        'form': form,
        'staff': staff,
        'submitted': submitted,
        'treatment_summary': treatment_summary,
        'medical_transactions': medical_transactions,
        'medical_trans_count': medical_trans_count,
        'company_info': company_info,
        'academic_years': academic_years,
        'hospitals': hospitals,
        'RELATIONSHIP': ChoicesDependants.objects.all().values_list("name", "name"),
        'MEDICALTREATMENT': ChoicesMedicalTreatment.objects.all().values_list("name", "name"),
        'MEDICALTYPE': ChoicesMedicalType.objects.all().values_list("name", "name"),
        'BENE': final_bene_list,
        'active_year': active_year_value,
    }
    return render(request, 'hr/medical.html', context)



@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('modify_medical_bill')
def edit_medical_transaction(request, staffno, med_id):
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = get_object_or_404(CompanyInformation, staffno=staff)
    medical_transaction = get_object_or_404(Medical, pk=med_id)
    academic_years = AcademicYear.objects.all()
    hospitals = Hospital.objects.all()

    # Get active academic year
    active_year = AcademicYear.objects.filter(active=True).first()
    active_year_value = active_year.academic_year if active_year else None

    # Get all entitlements for this staff category in the active year
    entitlements = MedicalEntitlement.objects.filter(
        staff_cat=company_info.staff_cat,
        academic_year=active_year_value
    )

    if not entitlements.exists():
        messages.error(request, f"No medical entitlement set for {company_info.staff_cat} in {active_year_value}.")
        return redirect('medical-entitlement')

    # Load beneficiaries
    bene_list = Kith.objects.filter(staffno=staff).annotate(
        full_name=Concat(
            F('kith_fname'), Value(' '),
            F('kith_middlenames'), Value(' '),
            F('kith_lname'),
            output_field=CharField()
        )
    ).values_list('full_name', 'full_name')
    staff_fullname = f"{staff.title} {staff.fname} {staff.lname}"
    final_bene_list = list(bene_list) + [(staff_fullname, staff_fullname)]

    if request.method == 'POST':
        form = MedicalTransactionForm(request.POST, instance=medical_transaction)
        if form.is_valid():
            updated_transaction = form.save(commit=False)
            treatment_type = updated_transaction.nature
            academic_year = updated_transaction.academic_year
            
            selected_key = updated_transaction.patient_name
            bene_dict = dict(final_bene_list)
            patient_name = bene_dict.get(selected_key, selected_key)

            # Get the correct entitlement for updated treatment type
            medical_entitlement = entitlements.filter(treatment_type=treatment_type).first()

            if not medical_entitlement:
                messages.error(request, f"No entitlement found for {treatment_type} in {academic_year}.")
                return redirect('medical-transaction', staffno=staffno)

            updated_transaction.staffno = staff
            updated_transaction.staff_cat = company_info.staff_cat
            updated_transaction.patient_name = patient_name
            updated_transaction.save()

            messages.success(request, f'Medical transaction updated successfully for {staff_fullname}.')
            return redirect('medical-transaction', staffno=staffno)
        else:
            messages.error(request, 'Form is not valid.')
            print(form.errors)
    else:
        form = MedicalTransactionForm(instance=medical_transaction)

    context = {
        'form': form,
        'staff': staff,
        'medical_transaction': medical_transaction,
        'company_info': company_info,
        'academic_years': academic_years,
        'hospitals': hospitals,
        'RELATIONSHIP': ChoicesDependants.objects.all().values_list("name", "name"),
        'MEDICALTREATMENT': ChoicesMedicalTreatment.objects.all().values_list("name", "name"),
        'MEDICALTYPE': ChoicesMedicalType.objects.all().values_list("name", "name"),
        'BENE': final_bene_list,
        'active_year': active_year_value,
    }

    return render(request, 'hr/medical.html', context)


######################################################################
### Staff education views
######################################################################
@login_required
def staff_education(request,staffno):
    submitted = False
    school_list = School.objects.order_by('school_name')
    staff = Employee.objects.get(pk=staffno)
    schools = Staff_School.objects.order_by('start_date').filter(staffno__exact=staffno)
    if request.method == 'POST':
        form = StaffSchoolForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('staff-education', staffno)
    else:
        form = StaffSchoolForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'HEQ':ChoicesHEQ.objects.all().values_list("name","name"),'form':form,'schools':schools,'staff':staff,'school_list':school_list,'submitted':submitted}
    return render(request,'hr/staff_education.html',context)

@login_required
def edit_staff_education(request,sch_id,staffno):
    school_list = School.objects.order_by('school_name')
    staff = Employee.objects.get(pk=staffno)
    schools = Staff_School.objects.order_by('start_date').filter(staffno__exact=staffno)
    sch_count = schools.count()
    school = Staff_School.objects.get(pk=sch_id)
    pkno = school.school_code_id
    form = StaffSchoolForm(request.POST or None,instance=school)

    if request.method == 'POST':
        form = StaffSchoolForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            return redirect('staff-education', staffno)

    context = {'HEQ':HEQ,'form':form,'schools':schools,'sch_count':sch_count,'school':school,'staff':staff,'school_list':school_list,'pkno':pkno}
    return render(request, 'hr/staff_education.html', context)    
    
@login_required
def delete_staff_education(request,sch_id,staffno):
    school = Staff_School.objects.get(pk=sch_id)
    school = school.school_code
    if request.method == 'POST':
       school.delete()
       return redirect('staff-education', staffno)
    return render(request, 'delete.html',{'obj':school})


######################################################################
### Staff Previous Work
######################################################################
@login_required
def prev_work(request,staffno):
    submitted = False
    company_list = Prev_Company.objects.order_by('start_date')
    staff = Employee.objects.get(pk=staffno)
    companys = Prev_Company.objects.order_by('start_date').filter(staffno__exact=staffno)
    if request.method == 'POST':
        form = StaffCompanyForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('prev-work', staffno)
        else:
            print(form.errors)
    else:
        form = StaffCompanyForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'companys':companys,'staff':staff,'company_list':company_list,'submitted':submitted}
    return render(request,'hr/prev_work.html',context)

@login_required
def edit_prev_work(request,coy_id,staffno):
    company_list = Prev_Company.objects.order_by('coy_name')
    staff = Employee.objects.get(pk=staffno)
    companys = Prev_Company.objects.order_by('start_date').filter(staffno__exact=staffno)
    coy_count = companys.count()
    company = Prev_Company.objects.get(pk=coy_id)
    # pkno = company.coy_code_id
    form = StaffCompanyForm(request.POST or None,instance=company)

    if request.method == 'POST':
        form = StaffCompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            return redirect('prev-work', staffno)

    context = {'form':form,'companys':companys,'coy_count':coy_count,'company':company,'staff':staff,'company_list':company_list}
    return render(request, 'hr/prev_work.html', context)

@login_required
def delete_prev_work(request,coy_id,staffno):
    company = Prev_Company.objects.get(pk=coy_id)
    # company = company.coy_name
    if request.method == 'POST':
       company.delete()
       return redirect('prev-work', staffno)
    return render(request, 'delete.html',{'obj':company.coy_name})


######################################################################
### Staff Residential Address
######################################################################
def res_address(request,staffno):
    submitted = False
    resaddress_list = Res_Address.objects.all()
    staff = Employee.objects.get(pk=staffno)
    resaddresses = Res_Address.objects.filter(staffno__exact=staffno)
    if request.method == 'POST':
        form = ResAddressForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('res-address', staffno)
    else:
        form = ResAddressForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'resaddresses':resaddresses,'staff':staff,'resaddress_list':resaddress_list,'submitted':submitted,'GENDER':GENDER,'DEPENDANTS':DEPENDANTS}
    return render(request,'hr/res_address.html',context)

def edit_res_address(request,ra_id,staffno):
    resaddress_list = Res_Address.objects.all()
    staff = Employee.objects.get(pk=staffno)
    resaddresses = Res_Address.objects.filter(staffno__exact=staffno)
    coy_count = resaddresses.count()
    resaddress = Res_Address.objects.get(pk=ra_id)
    pkno = resaddress.id
    form = ResAddressForm(request.POST or None,instance=resaddress)

    if request.method == 'POST':
        form = ResAddressForm(request.POST, instance=resaddress)
        if form.is_valid():
            form.save()
            return redirect('res-address', staffno)

    context = {'pkno':pkno,'form':form,'resaddresses':resaddresses,'coy_count':coy_count,'resaddress':resaddress,'staff':staff,'resaddress_list':resaddress_list,'GENDER':GENDER,'DEPENDANTS':DEPENDANTS}
    return render(request, 'hr/res_address.html', context)


def delete_res_address(request,ra_id,staffno):
    resaddress = Res_Address.objects.get(pk=ra_id)
    # resaddress = resaddress.coy_name
    if request.method == 'POST':
       resaddress.delete()
       return redirect('res-address', staffno)
    return render(request, 'delete.html',{'obj':resaddress})

######################################################################
### End of Staff Residential Address
######################################################################

######################################################################
### Staff Postal Address
######################################################################
def post_address(request,staffno):
    submitted = False
    postaddress_list = Postal_Address.objects.all()
    staff = Employee.objects.get(pk=staffno)
    postaddresses = Postal_Address.objects.filter(staffno__exact=staffno)
    if request.method == 'POST':
        form = PostAddressForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('post-address', staffno)
    else:
        form = PostAddressForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'postaddresses':postaddresses,'staff':staff,'postaddress_list':postaddress_list,'submitted':submitted,'GENDER':GENDER,'DEPENDANTS':DEPENDANTS}
    return render(request,'hr/post_address.html',context)

def edit_post_address(request,post_id,staffno):
    postaddress_list = Postal_Address.objects.all()
    staff = Employee.objects.get(pk=staffno)
    postaddresses = Postal_Address.objects.filter(staffno__exact=staffno)
    coy_count = postaddresses.count()
    postaddress = Postal_Address.objects.get(pk=post_id)
    pkno = postaddress.id
    form = PostAddressForm(request.POST or None,instance=postaddress)

    if request.method == 'POST':
        form = PostAddressForm(request.POST, instance=postaddress)
        if form.is_valid():
            form.save()
            return redirect('post-address', staffno)

    context = {'pkno':pkno,'form':form,'postaddresses':postaddresses,'coy_count':coy_count,'postaddress':postaddress,'staff':staff,'postaddress_list':postaddress_list,'GENDER':GENDER,'DEPENDANTS':DEPENDANTS}
    return render(request, 'hr/post_address.html', context)


def delete_post_address(request,post_id,staffno):
    postaddress = Postal_Address.objects.get(pk=post_id)
    # postaddress = postaddress.coy_name
    if request.method == 'POST':
       postaddress.delete()
       return redirect('post-address', staffno)
    return render(request, 'delete.html',{'obj':postaddress})

######################################################################
### End of Staff Postal Address
######################################################################


######################################################################
### Staff Vehicle
######################################################################
def vehicle(request,staffno):
    submitted = False
    vehicle_list = Vehicle.objects.all()
    staff = Employee.objects.get(pk=staffno)
    vehicles = Vehicle.objects.filter(staffno__exact=staffno)
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('vehicle', staffno)
    else:
        form = VehicleForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'vehicles':vehicles,'staff':staff,'vehicle_list':vehicle_list,'submitted':submitted}
    return render(request,'hr/vehicle.html',context)

def edit_vehicle(request,veh_id,staffno):
    vehicle_list = Vehicle.objects.all()
    staff = Employee.objects.get(pk=staffno)
    vehicles = Vehicle.objects.filter(staffno__exact=staffno)
    coy_count = vehicles.count()
    vehicle = Vehicle.objects.get(pk=veh_id)
    pkno = vehicle.id
    form = VehicleForm(request.POST or None,instance=vehicle)

    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            return redirect('vehicle', staffno)

    context = {'pkno':pkno,'form':form,'vehicles':vehicles,'coy_count':coy_count,'vehicle':vehicle,'staff':staff,'vehicle_list':vehicle_list}
    return render(request, 'hr/vehicle.html', context)


def delete_vehicle(request,veh_id,staffno):
    vehicle = Vehicle.objects.get(pk=veh_id)
    # vehicle = vehicle.coy_name
    if request.method == 'POST':
       vehicle.delete()
       return redirect('vehicle', staffno)
    return render(request, 'delete.html',{'obj':vehicle.car_no})

######################################################################
### End of Staff Vehicle
######################################################################

######################################################################
### Staff Bank
######################################################################
def staffbank(request,staffno):
    submitted = False
    bank_list = Bank.objects.all()
    bank_branches = BankBranch.objects.all()
    staff = Employee.objects.get(pk=staffno)
    staffbanks = StaffBank.objects.filter(staffno__exact=staffno)
    if request.method == 'POST':
        form = StaffBankForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('staffbank', staffno)
    else:
        form = StaffBankForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'staffbanks':staffbanks,'staff':staff,'bank_list':bank_list,'submitted':submitted,'bank_branches':bank_branches}
    return render(request,'hr/staffbank.html',context)

def edit_staffbank(request,bk_id,staffno):
    bank_list = Bank.objects.all()
    bank_branches = BankBranch.objects.all()
    staff = Employee.objects.get(pk=staffno)
    staffbanks = StaffBank.objects.filter(staffno__exact=staffno)
    coy_count = staffbanks.count()
    staffbank = StaffBank.objects.get(pk=bk_id)
    pkno = staffbank.bank_id
    form = StaffBankForm(request.POST or None,instance=staffbank)

    if request.method == 'POST':
        form = StaffBankForm(request.POST, instance=staffbank)
        if form.is_valid():
            form.save()
            return redirect('staffbank', staffno)

    context = {'bank_branches':bank_branches,'pkno':pkno,'form':form,'staffbanks':staffbanks,'coy_count':coy_count,'staffbank':staffbank,'staff':staff,'bank_list':bank_list}
    return render(request, 'hr/staffbank.html', context)


def delete_staffbank(request,bk_id,staffno):
    staffbank = StaffBank.objects.get(pk=bk_id)
    # bank = bank.coy_name
    if request.method == 'POST':
       staffbank.delete()
       return redirect('staffbank', staffno)
    return render(request, 'delete.html',{'obj':staffbank})

######################################################################
### End of Staff Bank
######################################################################

######################################################################
### Staff Promotion
######################################################################
def promotion(request,staffno):
    submitted = False
    jobtitle_list = JobTitle.objects.all()
    current_rank = Promotion.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    promotions = Promotion.objects.filter(staffno__exact=staffno).order_by('-effective_date')
    # promotion = Promotion.objects.get(pk=bk_id)
    if request.method == 'POST':
        form = PromotionForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('promotion', staffno)
    else:
        form = PromotionForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'current_rank':current_rank,'form':form,'promotions':promotions,'staff':staff,'jobtitle_list':jobtitle_list,'submitted':submitted,'STAFFRANK':ChoicesStaffRank.objects.all().values_list("name","name")}
    return render(request,'hr/promotion.html',context)

def edit_promotion(request,bk_id,staffno):
    jobtitle_list = JobTitle.objects.all()
    promotion_list = Promotion.objects.all()
    current_rank = Promotion.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    promotions = Promotion.objects.filter(staffno__exact=staffno).order_by('-effective_date')
    coy_count = promotions.count()
    promotion = Promotion.objects.get(pk=bk_id)
    pkno = promotion.id
    form = PromotionForm(request.POST or None,instance=promotion)

    if request.method == 'POST':
        form = PromotionForm(request.POST, instance=promotion)
        if form.is_valid():
            form.save()
            return redirect('promotion', staffno)

    context = {'jobtitle_list':jobtitle_list,'current_rank':current_rank,'pkno':pkno,'form':form,'promotions':promotions,'coy_count':coy_count,'promotion':promotion,'staff':staff,'promotion_list':promotion_list,'STAFFRANK':STAFFRANK}
    return render(request, 'hr/promotion.html', context)


def delete_promotion(request,bk_id,staffno):
    promotion = Promotion.objects.get(pk=bk_id)
    # promotion = promotion.coy_name
    if request.method == 'POST':
       promotion.delete()
       return redirect('promotion', staffno)
    return render(request, 'delete.html',{'obj':promotion.new_jobtitle})

######################################################################
### End of Promotion
######################################################################

######################################################################
### Staff Transfers
######################################################################
def transfer(request,staffno):
    submitted = False
    transfer_list = Transfer.objects.all()
    current_rank = Transfer.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    transfers = Transfer.objects.filter(staffno__exact=staffno).order_by('-effective_date')
    # transfer = Transfer.objects.get(pk=bk_id)
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('transfer', staffno)
    else:
        form = TransferForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'current_rank':current_rank,'form':form,'transfers':transfers,
               'staff':staff,'transfer_list':transfer_list,'submitted':submitted,
               'DEPARTMENT':DEPARTMENT,'BRANCH':BRANCH,'OFFICE':OFFICE}
    return render(request,'hr/transfer.html',context)

def edit_transfer(request,bk_id,staffno):
    transfer_list = Transfer.objects.all()
    current_rank = Transfer.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    transfers = Transfer.objects.filter(staffno__exact=staffno).order_by('-effective_date')
    coy_count = transfers.count()
    transfer = Transfer.objects.get(pk=bk_id)
    pkno = transfer.id
    form = TransferForm(request.POST or None,instance=transfer)

    if request.method == 'POST':
        form = TransferForm(request.POST, instance=transfer)
        if form.is_valid():
            form.save()
            return redirect('transfer', staffno)

    context = {'transfer_list':transfer_list,'current_rank':current_rank,'pkno':pkno,
               'form':form,'transfers':transfers,'coy_count':coy_count,'transfer':transfer,
               'staff':staff,'transfer_list':transfer_list,
               'DEPARTMENT':DEPARTMENT,'BRANCH':BRANCH,'OFFICE':OFFICE}
    return render(request, 'hr/transfer.html', context)


def delete_transfer(request,bk_id,staffno):
    staff = Employee.objects.get(pk=staffno)
    transfer = Transfer.objects.get(pk=bk_id)
    # transfer = transfer.coy_name
    if request.method == 'POST':
       transfer.delete()
       return redirect('transfer', staffno)
    return render(request, 'delete.html',{'obj':staff})

######################################################################
### End of Transfer
######################################################################

######################################################################
### Staff Bereavement
######################################################################
def bereavement(request,staffno):
    submitted = False
    bereavement_list = Bereavement.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    if request.method == 'POST':
        form = BereavementForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('bereavement',staffno)
    else:
        form = BereavementForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'bereavement_list':bereavement_list,'submitted':submitted,'staff':staff,'DEPENDANTS':ChoicesDependants.objects.all().values_list("name","name")}
    return render(request,'hr/bereavement.html',context)

def edit_bereavement(request,bno,staffno):
    staff = Employee.objects.get(pk=staffno)
    bereavement_list = Bereavement.objects.filter(staffno__exact=staffno)
    bereavement = Bereavement.objects.get(pk=bno)
    form = BereavementForm(request.POST or None,instance=bereavement)

    if request.method == 'POST':
        form = BereavementForm(request.POST, instance=bereavement)
        if form.is_valid():
            form.save()
            return redirect('bereavement',staffno)

    context = {'bereavement_list':bereavement_list,
               'form':form,'staff':staff,'DEPENDANTS':DEPENDANTS,'bereavement':bereavement
               }
    return render(request, 'hr/bereavement.html', context)


def delete_bereavement(request,bno,staffno):
    staff = Employee.objects.get(pk=staffno)
    bereavement = Bereavement.objects.get(pk=bno)
    if request.method == 'POST':
       bereavement.delete()
       return redirect('bereavement',staffno)
    return render(request, 'delete.html',{'obj':bereavement.deceased,'staff':staff,'DEPENDANTS':DEPENDANTS})

######################################################################
### End of Bereavement
######################################################################

######################################################################
### Staff Marriage
######################################################################
def marriage(request,staffno):
    submitted = False
    marriage_list = Marriage.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    if request.method == 'POST':
        form = MarriageForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('marriage',staffno)
    else:
        form = MarriageForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'marriage_list':marriage_list,'submitted':submitted,'staff':staff,'DEPENDANTS':ChoicesDependants.objects.all().values_list("name","name")}
    return render(request,'hr/marriage.html',context)

def edit_marriage(request,bno,staffno):
    staff = Employee.objects.get(pk=staffno)
    marriage_list = Marriage.objects.filter(staffno__exact=staffno)
    marriage = Marriage.objects.get(pk=bno)
    form = MarriageForm(request.POST or None,instance=marriage)

    if request.method == 'POST':
        form = MarriageForm(request.POST, instance=marriage)
        if form.is_valid():
            form.save()
            return redirect('marriage',staffno)

    context = {'marriage_list':marriage_list,
               'form':form,'staff':staff,'DEPENDANTS':DEPENDANTS,'marriage':marriage
               }
    return render(request, 'hr/marriage.html', context)


def delete_marriage(request,bno,staffno):
    staff = Employee.objects.get(pk=staffno)
    marriage = Marriage.objects.get(pk=bno)
    if request.method == 'POST':
       marriage.delete()
       return redirect('marriage',staffno)
    return render(request, 'delete.html',{'obj':marriage.celebrant,'staff':staff,'DEPENDANTS':DEPENDANTS})

######################################################################
### End of Marriage
######################################################################

######################################################################
### Staff Christening
######################################################################
def christening(request,staffno):
    submitted = False
    christening_list = Christening.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    if request.method == 'POST':
        form = ChristeningForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('christening',staffno)
    else:
        form = ChristeningForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'christening_list':christening_list,'submitted':submitted,'staff':staff,'DEPENDANTS':DEPENDANTS}
    return render(request,'hr/christening.html',context)

def edit_christening(request,bno,staffno):
    staff = Employee.objects.get(pk=staffno)
    christening_list = Christening.objects.filter(staffno__exact=staffno)
    christening = Christening.objects.get(pk=bno)
    form = ChristeningForm(request.POST or None,instance=christening)

    if request.method == 'POST':
        form = ChristeningForm(request.POST, instance=christening)
        if form.is_valid():
            form.save()
            return redirect('christening',staffno)

    context = {'christening_list':christening_list,
               'form':form,'staff':staff,'DEPENDANTS':DEPENDANTS,'christening':christening
               }
    return render(request, 'hr/christening.html', context)


def delete_christening(request,bno,staffno):
    staff = Employee.objects.get(pk=staffno)
    christening = Christening.objects.get(pk=bno)
    if request.method == 'POST':
       christening.delete()
       return redirect('christening',staffno)
    return render(request, 'delete.html',{'obj':"This christening",'staff':staff})

######################################################################
### End of Christening
######################################################################

######################################################################
### Staff Celebration
######################################################################
def celebration(request,staffno):
    submitted = False
    celebration_list = Celebration.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    if request.method == 'POST':
        form = CelebrationForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('celebration',staffno)
    else:
        form = CelebrationForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'celebration_list':celebration_list,'submitted':submitted,'staff':staff}
    return render(request,'hr/celebration.html',context)

def edit_celebration(request,bno,staffno):
    staff = Employee.objects.get(pk=staffno)
    celebration_list = Celebration.objects.filter(staffno__exact=staffno)
    celebration = Celebration.objects.get(pk=bno)
    form = CelebrationForm(request.POST or None,instance=celebration)

    if request.method == 'POST':
        form = CelebrationForm(request.POST, instance=celebration)
        if form.is_valid():
            form.save()
            return redirect('celebration',staffno)

    context = {'celebration_list':celebration_list,
               'form':form,'staff':staff,'DEPENDANTS':DEPENDANTS,'celebration':celebration
               }
    return render(request, 'hr/celebration.html', context)


def delete_celebration(request,bno,staffno):
    staff = Employee.objects.get(pk=staffno)
    celebration = Celebration.objects.get(pk=bno)
    if request.method == 'POST':
       celebration.delete()
       return redirect('celebration',staffno)
    return render(request, 'delete.html',{'obj':"This celebration",'staff':staff})

######################################################################
### End of Celebration
######################################################################

# View for adding a new renewal history
@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('renewal_record')
def add_renewal_history(request, staffno):
    submitted = False
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = get_object_or_404(CompanyInformation, staffno=staff)
    renewal_list = RenewalHistorys.objects.filter(staffno=staff)
    renewal_count = renewal_list.count()
    staffcategory = StaffCategory.objects.all()
    jobtitle = JobTitle.objects.all()
    ranks = StaffRank.objects.all()
    

    
    if request.method == 'POST':
        form = RenewalHistoryForm(request.POST)
        if form.is_valid():
            renewal = form.save(commit=False)
            renewal.staffno = staff
            renewal.is_approved = False
            renewal.save()
            messages.success(request, "New renewal history added successfully, waiting approval.")
            logger.info(f"New renewal history added for {staff.staffno} by {request.user.username}.")
            return redirect('renewal-history', staffno)
        else:
            messages.error(request, "Form is not valid. Please check the data.")            
    else:
        form = RenewalHistoryForm()
        if 'submitted' in request.GET:
            submitted = True
            
    context = {
        'form': form, 
        'submitted': submitted, 
        'staff': staff, 
        'renewal_list': renewal_list, 
        'renewal_count':renewal_count,
        'staffcategory':staffcategory,
        'jobtitle':jobtitle,
        'ranks': ranks,
        'company_info':company_info,
    }
    
    return render(request, 'hr/renewal.html', context)


# View for approving a renewal history
@login_required
@role_required(['superadmin', 'hr admin'])
def approve_renewal(request, renewal_id):
    renewal = get_object_or_404(RenewalHistorys, id=renewal_id)

    if request.method == 'POST':
        # approval status directly
        renewal.is_approved = True
        renewal.approved_by = request.user
        renewal.save()
        
        messages.success(request, f"Renewal for {renewal.staffno} has been approved.")
        logger.info(f"Renewal for {renewal.staffno} has been approved by {request.user.username}.")
        return redirect('staff-details', staffno=renewal.staffno.staffno)

    return redirect('landing')

# View for rejecting a renewal history
@login_required
@role_required(['superadmin', 'hr admin'])
def disapprove_renewal(request, renewal_id):
    renewal = get_object_or_404(RenewalHistorys, id=renewal_id)

    if request.method == 'POST':
        # approval status directly
        renewal.is_disapproved = True
        renewal.approved_by = request.user
        renewal.save()

        messages.success(request, f"Renewal for {renewal.staffno} has been rejected.")
        logger.info(f"Renewal for {renewal.staffno} has been rejected by {request.user.username}.")
        return redirect('staff-details', staffno=renewal.staffno.staffno)

    return redirect('landing')


# View for adding new promotion history
@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('promotion_record')
def add_promotion_history(request, staffno):
    submitted = False
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = get_object_or_404(CompanyInformation, staffno=staff)
    promotion_list = PromotionHistory.objects.filter(staffno=staff)
    promotion_count = promotion_list.count()
    staffcategory = StaffCategory.objects.all()
    jobtitle = JobTitle.objects.all()
    ranks = StaffRank.objects.all()
    


    if request.method == 'POST':
        form = PromotionHistoryForm(request.POST)
        if form.is_valid():
            promotion = form.save(commit=False)
            promotion.staffno = staff
            promotion.is_approved = False
            promotion.save()
            messages.success(request, "New promotion history added successfully, waiting approval.")
            logger.info(f"New promotion history added for {staff.staffno} by {request.user.username}.")
            return redirect('promotion-history', staffno)
        else:
            messages.error(request, "Form is not valid. Please check the data.")
    else:
        form = PromotionHistoryForm()
        if 'submitted' in request.GET:
            submitted = True

    context = {
        'form': form,
        'submitted': submitted,
        'staff': staff,
        'promotion_list': promotion_list,
        'promotion_count':promotion_count,
        'staffcategory':staffcategory,
        'jobtitle':jobtitle,
        'ranks':ranks,
        'company_info':company_info,
    }

    return render(request, 'hr/promotion.html', context)

# View for approving a promotion history
@login_required
@role_required(['superadmin', 'hr admin'])
def approve_promotion(request, promotion_id):
    promotion = get_object_or_404(PromotionHistory, id=promotion_id)

    if request.method == 'POST':
        # approval status directly
        promotion.is_approved = True
        promotion.approved_by = request.user
        promotion.save()

        messages.success(request, f"Promotion for {promotion.staffno} has been approved.")
        logger.info(f"Promotion for {promotion.staffno} has been approved by {request.user.username}.")
        return redirect('staff-details', staffno=promotion.staffno.staffno)

    return redirect('landing')

# View for rejecting a promotion history
@login_required
@role_required(['superadmin', 'hr admin'])
def disapprove_promotion(request, promotion_id):
    promotion = get_object_or_404(PromotionHistory, id=promotion_id)

    if request.method == 'POST':
        # approval status directly
        promotion.is_disapproved = True
        promotion.approved_by = request.user
        promotion.save()

        messages.success(request, f"Promotion for {promotion.staffno} has been rejected.")
        logger.info(f"Promotion for {promotion.staffno} has been rejected by {request.user.username}.")
        return redirect('staff-details', staffno=promotion.staffno.staffno)

    return redirect('landing')



@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('exits_record')
def add_exit_history(request, staffno):
    submitted = False
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = get_object_or_404(CompanyInformation, staffno=staff)
    exit_list = Exits.objects.filter(staffno=staff)
    exit_count = exit_list.count()
    approvers_list = User.objects.filter(is_superuser='True')
    
    if request.method == 'POST':
        form = ExitHistoryForm(request.POST)
        if form.is_valid():
            exit_history = form.save(commit=False)
            exit_history.staffno = staff
            exit_history.is_approved = False
            exit_history.save()
            messages.success(request, "New exit history added successfully, waiting approval.")
            logger.info(f"New exit history added for {staff.staffno} by {request.user.username}.")
            return redirect('exit-history', staffno)
        else:
            messages.error(request, "Form is not valid. Please check the data.")
            print(form.errors)
    else:
        form = ExitHistoryForm()
        if 'submitted' in request.GET:
            submitted = True

    context = {
        'form': form,
        'submitted': submitted,
        'staff': staff,
        'exit_list': exit_list,
        'exit_count':exit_count,
        'company_info':company_info,
        'approvers_list':approvers_list,
        'EXITTYPE': ChoicesExitType.objects.all().values_list("name", "name"),
    }

    return render(request, 'hr/exit.html', context)



@login_required
@role_required(['superadmin', 'hr admin'])
def approve_exit(request, exit_id):
    exit_history = get_object_or_404(Exits, id=exit_id)

    if request.method == 'POST':
        # approval status directly
        exit_history.is_approved = True
        exit_history.approved_by = request.user
        exit_history.save()

        messages.success(request, f"Exit for {exit_history.staffno} has been approved.")
        logger.info(f"Exit for {exit_history.staffno} has been approved by {request.user.username}.")
        return redirect('staff-details', staffno=exit_history.staffno.staffno)

    return redirect('landing')


@login_required
@role_required(['superadmin', 'hr admin'])
def disapprove_exit(request, exit_id):
    exit_history = get_object_or_404(Exits, id=exit_id)

    if request.method == 'POST':
        # approval status directly
        exit_history.is_disapproved = True
        exit_history.approved_by = request.user
        exit_history.save()

        messages.success(request, f"Exit for {exit_history.staffno} has been rejected.")
        logger.info(f"Exit for {exit_history.staffno} has been rejected by {request.user.username}.")
        return redirect('staff-details', staffno=exit_history.staffno.staffno)

    return redirect('landing')




@login_required
@role_required(['superadmin', 'hr admin', 'hr officer'])
def staff_settings(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    
    context = {
        'staff': staff,
        'company_info':company_info,    
    }
    return render(request, 'hr/staff_settings.html', context)
        
@login_required
@role_required(['superadmin', 'hr admin', 'hr officer'])
def mark_dormant(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    full_name = f"{staff.title} {staff.fname} {staff.lname}"
    print(company_info.active_status)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'inactive':
            company_info.active_status = 'Inactive'
            messages.success(request, f"{full_name} marked as Inactive.")
            logger.info(f"{request.user.username} marked {full_name} as Inactive.")
        elif action == 'reactivate':
            company_info.active_status = 'Active'
            messages.success(request, f"{full_name} reactivated.")
            logger.info(f"{request.user.username} reactivated {full_name}.")

        company_info.save()

    return redirect('staff-settings', staffno=staffno)


# Groups and Permissions
@login_required
@role_required(['superadmin'])
def create_groups(request):
    groups = Group.objects.all()
    permissions = Permission.objects.all()

    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        print(group_name)
        if group_name:
            Group.objects.create(name=group_name)
            messages.success(request, 'Group created successfully.')
            return redirect('create-groups')

    return render(request, 'roles/create_group.html', {
        'groups': groups,
        'permissions': permissions,
    })
    
@login_required
@role_required(['superadmin'])
def assign_permissions_to_group(request, group_id):
    group = Group.objects.get(id=group_id)
    permissions = Permission.objects.all()

    if request.method == 'POST':
        selected_permissions = request.POST.getlist('permissions', ) 
        group.permissions.set(selected_permissions)
        messages.success(request, 'Permissions assigned successfully.')
        return redirect('create-groups')

    return render(request, 'roles/assign_permissions.html', {
        'group': group,
        'permissions': permissions,
    })
    
@login_required
@role_required(['superadmin'])
def assign_user_to_group(request):
    users = User.objects.all()
    groups = Group.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        group_id = request.POST.get('group_id')

        user = User.objects.get(id=user_id)
        group = Group.objects.get(id=group_id)

        user.groups.add(group)  # Add user to group
        messages.success(request, 'User assigned to group successfully.')
        return redirect('assign-user-group')  # Adjust as needed

    return render(request, 'roles/assign_user_group.html', {
        'users': users,
        'groups': groups,
    })
    

@login_required
@role_required(['superadmin', 'hr admin', 'finance admin'])
def manage_users(request):
    users = User.objects.all()
    groups = Group.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        group_id = request.POST.get('group_id')
        
        if not group_id:
            messages.error(request, "Please select a valid group before assigning.")
            return redirect('manage-users')

        user = User.objects.get(id=user_id)
        group = Group.objects.get(id=group_id)
        user.groups.add(group)
        messages.success(request, f"{user.username} has been assigned to {group.name} successfully.")
        logger.info(f"{user.username} has been assigned to {group.name} by {request.user.username}.")
        return redirect('manage-users')

    return render(request, 'roles/manage_users.html', {
        'users': users,
        'groups': groups,
    })


@login_required
@role_required(['superadmin'])
def approve_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.approval = True
    user.save()
    messages.success(request, f"User {user.username} has been approved!")
    logger.info(f"User {user.username} has been approved by {request.user.username}.")
    return redirect('edit-user-permissions', user_id)


@login_required
@role_required(['superadmin'])
def disapprove_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, f"User {user.username} has been disapproved!")
    logger.info(f"User {user.username} has been disapproved by {request.user.username}.")
    return redirect('landing')


@login_required
@role_required(['superadmin', 'hr officer'])
def edit_user_permissions(request, user_id):
    user = get_object_or_404(User, id=user_id)
    groups = Group.objects.all()
    tags = PermissionTag.objects.all().order_by('-category', 'name')

    if request.method == 'POST':
        selected_group_ids = request.POST.getlist('groups')
        user.groups.set(Group.objects.filter(id__in=selected_group_ids))

        selected_tag_ids = request.POST.getlist('tags')
        UserTag.objects.filter(user=user).delete()
        for tag_id in selected_tag_ids:
            tag = PermissionTag.objects.get(id=tag_id)
            UserTag.objects.create(user=user, tag=tag)

        messages.success(request, f"Permissions updated for {user.username}")
        return redirect('manage-users')

    current_group_ids = user.groups.values_list('id', flat=True)
    current_tag_ids = list(UserTag.objects.filter(user=user).values_list('tag_id', flat=True))
    current_tag_ids = [int(id) for id in current_tag_ids]

    return render(request, 'roles/edit_user_permissions.html', {
        'user': user,
        'groups': groups,
        'tags': tags,
        'current_group_ids': current_group_ids,
        'current_tag_ids': current_tag_ids,
    })



######## Staff Documents ###########

@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('record_staff_documents')
def create_staff_document(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    staff_documents = StaffDocument.objects.filter(staffno__exact=staffno).order_by('-uploaded_at')
    staff_document_count = staff_documents.count()
    form = StaffDocumentForm(request.POST or None, request.FILES or None)

    
    if request.method == 'POST':
        title = request.POST.get('title')
        notes = request.POST.get('notes')
        doc_file = request.FILES.get('scanned_doc')

        if doc_file and title:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in doc_file.chunks():
                    temp_file.write(chunk)
                temp_file.flush()

                unique_filename = f"staff_documents/{uuid.uuid4().hex}_{doc_file.name}"
                firebase_url = upload_file_to_firebase(temp_file.name, unique_filename)

                # Save document to DB
                StaffDocument.objects.create(
                    staffno=staff,
                    title=title,
                    notes=notes,
                    doc_url=firebase_url
                )

                messages.success(request, f"{title} uploaded for {staff.fname} {staff.lname} successfully.")
                logger.info(f"{request.user.username} uploaded {title} for {staff.fname} {staff.lname}.")
                return redirect('staff-details', staffno=staffno)
        else:
            messages.error(request, "Title and document file are required.")
            return redirect('upload-document', staffno=staffno)

    context = {'form': form, 'staff': staff, 'staff_documents': staff_documents, 'staff_document_count': staff_document_count}
    return render(request, 'hr/upload_staff_document.html', context)



@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('delete_staff_document')
def delete_staff_document(request, doc_id, staffno):
    staff = Employee.objects.get(pk=staffno)
    staff_document = StaffDocument.objects.get(pk=doc_id)

    try:
        delete_file_from_firebase(staff_document.doc_url)
    except Exception as e:
        logger.warning(f"Failed to delete Firebase file: {e}")
        
    staff_document.delete()

    full_name = f"{staff.fname} {staff.lname}"
    messages.success(request, f"Document '{staff_document.title}' for {full_name} has been deleted successfully.")
    logger.info(f"{request.user.username} deleted document '{staff_document.title}' for {full_name}.")

    return redirect('staff-details', staffno=staffno)


########## INCOME DEDUCTION AND LOAN ###############

############ STAFF INCOME #############
@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('record_staff_income')
def create_staff_income(request, staffno):
    submitted = False
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    staff_incomes = StaffIncome.objects.filter(staffno__exact=staffno).order_by('income_type')
    staff_income_count = staff_incomes.count()
    income_types = IncomeType.objects.all().order_by('name')
    
    if request.method == 'POST':
        form = StaffIncomeForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data.get('amount')
            percentage_of_basic = form.cleaned_data.get('percentage_of_basic')
            print("Cleaned Data", form.cleaned_data)
                            
            if amount and percentage_of_basic:
                messages.error(request, "Please provide either amount or percentage on basic, not both.")
                messages.error(request, "Form is not valid. Please check the data.")
                
                return redirect('create-staff-income', staffno)
            elif not amount and not percentage_of_basic:
                messages.error(request, "Please provide either amount or percentage on basic.")
                return redirect('create-staff-income', staffno)
            else:
                form.save()
                messages.success(request, "Staff income added successfully.")
                return redirect('create-staff-income', staffno)
        else:
            print("Form Errors:", form.errors) 
    else:
        form = StaffIncomeForm()
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'staff_incomes':staff_incomes,'staff':staff,'company_info':company_info,'submitted':submitted,'staff_income_count':staff_income_count, 'income_types':income_types}
    return render(request, 'hr/staff_income.html', context)


@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('modify_staff_income')
def edit_staff_income(request, staffno, income_id):
    submitted = False
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    staff_incomes = StaffIncome.objects.filter(staffno__exact=staffno).order_by('income_type')
    staff_income = StaffIncome.objects.get(pk=income_id)
    staff_income_count = staff_incomes.count()
    income_types = IncomeType.objects.all()

    
    if request.method == 'POST':
        form = StaffIncomeForm(request.POST, instance=staff_income)
        if form.is_valid():
            amount = form.cleaned_data.get('amount')
            percentage_of_basic = form.cleaned_data.get('percentage_of_basic')
            
            if amount and percentage_of_basic:
                messages.error(request, "Please provide either amount or percentage on basic, not both.")
                return redirect('create-staff-income', staffno)
            elif not amount and not percentage_of_basic:
                messages.error(request, "Please provide either amount or percentage on basic.")
                return redirect('create-staff-income', staffno)
            else:
                form.save()
                messages.success(request, "Staff income updated successfully.")
                return redirect('create-staff-income', staffno)
    else:
        form = StaffIncomeForm(instance=staff_income)
        if 'submitted' in request.GET:
            submitted = True
    
    context = {'form':form,'staff_incomes':staff_incomes,'staff_income':staff_income, 'staff':staff,'company_info':company_info,'submitted':submitted,'staff_income_count':staff_income_count, 'income_types':income_types}
    
    return render(request, 'hr/staff_income.html', context)


############ STAFF DEDUCTIONS #############
@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('record_staff_deduction')
def create_staff_deduction(request, staffno):
    submitted = False
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    staff_deductions = StaffDeduction.objects.filter(staffno__exact=staffno).order_by('deduction_type')
    staff_deduction_count = staff_deductions.count()
    deduction_types = DeductionType.objects.all()
    
    if request.method == 'POST':
        form = StaffDeductionForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data.get('amount')
            percentage_of_basic = form.cleaned_data.get('percentage_of_basic')
            print("Cleaned Data", form.cleaned_data)
                            
            if amount and percentage_of_basic:
                messages.error(request, "Please provide either amount or percentage on basic, not both.")
                return redirect('create-staff-deduction', staffno)
            elif not amount and not percentage_of_basic:
                messages.error(request, "Please provide either amount or percentage on basic.")
                return redirect('create-staff-deduction', staffno)
            else:
                form.save()
                messages.success(request, "Staff deductions added successfully.")
                return redirect('create-staff-deduction', staffno)
        else:
            print("Form Errors:", form.errors) 
    else:
        form = StaffDeductionForm()
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'staff_deductions':staff_deductions,'staff':staff,'company_info':company_info,'submitted':submitted,'staff_deduction_count':staff_deduction_count, 'deduction_types':deduction_types}
    return render(request, 'hr/staff_deductions.html', context)


@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('modify_staff_deduction')
def edit_staff_deduction(request, staffno, deduction_id):
    submitted = False
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    staff_deductions = StaffDeduction.objects.filter(staffno__exact=staffno).order_by('deduction_type')
    staff_deduction = StaffDeduction.objects.get(pk=deduction_id)
    staff_deduction_count = staff_deductions.count()
    deduction_types = DeductionType.objects.all()
    
    if request.method == 'POST':
        form = StaffDeductionForm(request.POST, instance=staff_deduction)
        if form.is_valid():
            amount = form.cleaned_data.get('amount')
            percentage_of_basic = form.cleaned_data.get('percentage_of_basic')
            
            if amount and percentage_of_basic:
                messages.error(request, "Please provide either amount or percentage on basic, not both.")
                return redirect('create-staff-deduction', staffno)
            elif not amount and not percentage_of_basic:
                messages.error(request, "Please provide either amount or percentage on basic.")
                return redirect('create-staff-deduction', staffno)
            else:
                form.save()
                messages.success(request, "Staff deduction updated successfully.")
                return redirect('create-staff-deduction', staffno)
    else:
        form = StaffDeductionForm(instance=staff_deduction)
        if 'submitted' in request.GET:
            submitted = True
    
    context = {'form':form,'staff_deductions':staff_deductions,'staff_deduction': staff_deduction,'staff':staff,'company_info':company_info,'submitted':submitted,'staff_deduction_count':staff_deduction_count, 'deduction_types':deduction_types}
    
    return render(request, 'hr/staff_deductions.html', context)



@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('record_staff_relief')
def create_staff_relief(request, staffno):
    submitted = False
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    staff_reliefs = StaffRelief.objects.filter(staffno__exact=staffno).order_by('relief_type')
    staff_relief_count = staff_reliefs.count()
    relief_types = ReliefType.objects.all()

    if request.method == 'POST':
        form = StaffReliefForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff relief added successfully.")
            return redirect('create-staff-relief', staffno)
        else:
            print("Form Errors:", form.errors)
    else:
        form = StaffReliefForm()
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'staff_reliefs':staff_reliefs,'staff':staff,'company_info':company_info,'submitted':submitted,'staff_relief_count':staff_relief_count, 'relief_types':relief_types}
    return render(request, 'hr/staff_relief.html', context)


@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
@tag_required('modify_staff_deduction')
def edit_staff_relief(request, staffno, relief_id):
    submitted = False
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    staff_reliefs = StaffRelief.objects.filter(staffno__exact=staffno).order_by('relief_type')
    staff_relief = StaffRelief.objects.get(pk=relief_id)
    staff_relief_count = staff_reliefs.count()
    relief_types = ReliefType.objects.all()

    if request.method == 'POST':
        form = StaffReliefForm(request.POST, instance=staff_relief)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff relief updated successfully.")
            return redirect('create-staff-relief', staffno)
    else:
        form = StaffReliefForm(instance=staff_relief)
        if 'submitted' in request.GET:
            submitted = True

    context = {'form':form,'staff_reliefs':staff_reliefs,'staff_relief': staff_relief,'staff':staff,'company_info':company_info,'submitted':submitted,'staff_relief_count':staff_relief_count, 'relief_types':relief_types}

    return render(request, 'hr/staff_relief.html', context)



@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('record_staff_loan')
def create_staff_loan(request, staffno):
    submitted = False
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    staff_loans = StaffLoan.objects.filter(staffno=staff).order_by('-start_date')
    loan_types = ChoicesLoanType.objects.all()
    staff_loan_count = staff_loans.count()

    if request.method == 'POST':
        form = StaffLoanForm(request.POST)
        if form.is_valid():
            is_active = form.cleaned_data.get('is_active')
            loan_type = form.cleaned_data.get('loan_type')

            if is_active and StaffLoan.objects.filter(staffno=staff,loan_type=loan_type,is_active=True).exists():
                messages.error(request, f"Staff already has an active {loan_type} loan.")
                return redirect('create-staff-loan', staffno)

            loan = form.save(commit=False)
            loan.staffno = staff
            loan.save()
            messages.success(request, "Staff loan added successfully.")
            return redirect('create-staff-loan', staffno)
        else:
            messages.error(request, "Form is invalid. Check fields.")
            print("Form Errors:", form.errors)
    else:
        form = StaffLoanForm()
        if 'submitted' in request.GET:
            submitted = True

    context = {
        'form': form,
        'staff_loans': staff_loans,
        'staff': staff,
        'company_info': company_info,
        'loan_types': loan_types,
        'submitted':submitted,
        'staff_loan_count': staff_loan_count
    }
    return render(request, 'hr/staff_loan.html', context)


@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('modify_staff_loan')
def edit_staff_loan(request, staffno, loan_id):
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    staff_loans = StaffLoan.objects.filter(staffno=staff).order_by('-start_date')
    loan = get_object_or_404(StaffLoan, id=loan_id)
    staff_loan_count = staff_loans.count()

    if request.method == 'POST':
        is_active = request.POST.get('is_active') == 'true'
        loan.is_active = is_active
        loan.save()
        status = "activated" if is_active else "deactivated"
        messages.success(request, f"Loan has been {status} successfully.")
        return redirect('create-staff-loan', staffno)

    context = {
        'staff_loans': staff_loans,
        'staff': staff,
        'company_info': company_info,
        'loan': loan,
        'staff_loan_count': staff_loan_count
    }
    return render(request, 'hr/staff_loan.html', context)


########## END OF INCOME DEDUCTION AND LOAN ###############


@login_required
@role_required(["superadmin", "audit"])
def toggle_approval(request, payroll_id):
    payroll = get_object_or_404(Payroll, id=payroll_id)

    target_month = payroll.month.month 
    target_year = payroll.month.year 

    new_status = not payroll.is_approved

    Payroll.objects.filter(month__month=target_month, month__year=target_year).update(is_approved=new_status)

    status_text = "approved" if new_status else "unapproved"
    messages.success(request, f"Payroll for {payroll.month.strftime('%B %Y')} has been {status_text} successfully.")
    logger.info(f"Payroll for {payroll.month.strftime('%B %Y')} has been {status_text} by {request.user.username}.")

    return redirect("payroll-post-payroll")


########## GENERATE PAYROLL INFORMATION ###############
@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('finalise_payroll')
def generate_payroll(request):
    selected_month = request.POST.get("filter_by_month")
    selected_year = request.POST.get("filter_by_year")
    skipped_staff = []

    if selected_month and selected_year:        
        current_month_date = date(int(selected_year), int(selected_month), 28)
        
        # Block changes if already approved
        if Payroll.objects.filter(month=current_month_date, is_approved=True).exists():
            messages.error(request, f"Payroll for {current_month_date.strftime('%B %Y')} has already been approved and cannot be modified.")
            return redirect('payroll-post-payroll')
        
        # Enforce month-by-month finalization
        last_approved = Payroll.objects.filter(is_approved=True).order_by('-month').first()
        if last_approved:
            expected_next_month = (last_approved.month + relativedelta(months=1)).replace(day=28)
            if current_month_date != expected_next_month:
                messages.error(request, f"You must finalize payroll for {expected_next_month.strftime('%B %Y')} before proceeding.")
                return redirect('payroll-post-payroll')
        
        
        staff_list = Employee.objects.exclude(companyinformation__active_status='Inactive').order_by('lname')
        # staff_list = Employee.objects.filter(staffno="20034").exclude(companyinformation__active_status='Inactive').order_by('lname')
        
        for staff in staff_list:
            company_info = CompanyInformation.objects.filter(staffno=staff).first()
            if not company_info:
                continue  # skip if company info is missing
                
                
            try:
                payroll = PayrollCalculator(staffno=staff, month=current_month_date)     

                # Get or create payroll record for this staff and month
                payroll_obj, created = Payroll.objects.get_or_create(
                    staffno=staff,
                    month=current_month_date,
                    defaults={
                        'basic_salary': payroll.get_entitled_basic_salary(),
                        'total_income': payroll.get_gross_income() - payroll.get_entitled_basic_salary(),
                        'gross_salary': payroll.get_gross_income(),
                        'income_tax': payroll.get_income_tax()["tax"],
                        'other_deductions': payroll.get_deductions()["total_deduction"],
                        'ssf': payroll.get_ssnit_contribution()["amount"],
                        'pf_employee': payroll.get_pf_contribution()["amount"], 
                        'pf_employer': payroll.get_employer_pf_contribution(),
                        'total_deduction': payroll.get_total_deductions(),
                        'cost_center': company_info.cost_center,
                        'paye_total_income': payroll.get_miscellaneous_and_benefit_in_kind(),
                        'paye_total_emoluments': payroll.get_entitled_basic_salary() + payroll.get_miscellaneous_and_benefit_in_kind(),
                        'total_relief': payroll.get_staff_relief()["total_relief"],
                        'net_taxable_pay': payroll.get_taxable_income(),
                        'net_salary': payroll.get_net_salary(),
                    }
                )

                if not created:
                    # Update existing record
                    payroll_obj.basic_salary = payroll.get_entitled_basic_salary()
                    payroll_obj.total_income = payroll.get_gross_income() - payroll.get_entitled_basic_salary()
                    payroll_obj.gross_salary = payroll.get_gross_income()
                    payroll_obj.income_tax = payroll.get_income_tax()["tax"]
                    payroll_obj.other_deductions = payroll.get_deductions()["total_deduction"]
                    payroll_obj.ssf = payroll.get_ssnit_contribution()["amount"]
                    payroll_obj.pf_employee = payroll.get_pf_contribution()["amount"]
                    payroll_obj.pf_employer = payroll.get_employer_pf_contribution()
                    payroll_obj.total_deduction = payroll.get_total_deductions()
                    payroll_obj.net_salary = payroll.get_net_salary()
                    payroll_obj.cost_center = company_info.cost_center
                    payroll_obj.paye_total_income = payroll.get_miscellaneous_and_benefit_in_kind()
                    payroll_obj.paye_total_emoluments = payroll.get_entitled_basic_salary() + payroll.get_miscellaneous_and_benefit_in_kind()
                    payroll_obj.total_relief = payroll.get_staff_relief()["total_relief"]
                    payroll_obj.net_taxable_pay = payroll.get_taxable_income()
                    payroll_obj.save()
                    
                loan_deductions = payroll.get_active_loan_deductions()
                
                for loan in loan_deductions:
                    monthly_payment = loan["monthly_installment"]
                    loan_obj = StaffLoan.objects.filter(id=loan["id"]).first()
                    
                    if loan_obj:
                        # Get or create loan payment record for this month
                        loan_payment, created = LoanPayment.objects.get_or_create(
                            loan=loan_obj,
                            payment_date=current_month_date,
                            defaults={'amount_paid': monthly_payment}
                        )
                        
                        if created:
                            # Update loan object
                            loan_obj.months_left -= 1
                            if loan_obj.months_left <= 0:
                                loan_obj.is_active = False
                            loan_obj.save()
                        else:
                            # Update existing loan payment record
                            loan_payment.amount_paid = monthly_payment
                            loan_payment.save()
                        
            except (TypeError, InvalidOperation):
                skipped_staff.append(f"{staff.fname} {staff.lname} ({staff.staffno})")
                continue
        
        if skipped_staff:
            messages.error(request, f"The following staff were skipped due to missing basic salary: {', '.join(skipped_staff)}")

        messages.success(request, f"Payroll for {current_month_date.strftime('%B %Y')} has been finalised you can update once not approved")   
        logger.info(f"Payroll for {current_month_date.strftime('%B %Y')} has been finalised")     
        return redirect('payroll-post-payroll')
    
    payrolls_group = (
        Payroll.objects.values('month').annotate(latest_id=Max('id'), staff_count=Count('staffno')).order_by('-month'))

    payrolls = []
    for item in payrolls_group:
        payroll = Payroll.objects.get(id=item['latest_id'])
        payroll.staff_count = item['staff_count']
        payrolls.append(payroll)

        
    context = {"selected_month": selected_month, "payrolls":payrolls}
    return render(request, 'payroll/finalise_payroll.html', context)



@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('process_single_payroll')
def payroll_details(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    selected_month = request.GET.get("month")
    selected_year = request.GET.get("year")
    payroll_data = {}
    

    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)
        # current_month_date = date.fromisoformat(selected_month)
        payroll = PayrollCalculator(staffno=staff, month=selected_date)
        

        payroll_data = {
            "month": selected_date.strftime("%B %Y"),
            "basic_salary": payroll.get_entitled_basic_salary(),
            "total_income": payroll.get_gross_income() - payroll.get_entitled_basic_salary(),
            "gross_salary": payroll.get_gross_income(),
            "income_tax": payroll.get_income_tax(),
            "total_deduction": payroll.get_total_deductions(),
            "net_salary": payroll.get_net_salary(),
            "taxable_income": payroll.get_taxable_income(),
            "incomes": payroll.get_allowance_values()["incomes"],
            "deductions": payroll.get_deductions()["deductions"],
            "pf_employee": payroll.get_pf_contribution(),
            "ssf_employee": payroll.get_ssnit_contribution(),
            "employer_ssf": payroll.get_employer_ssnit_contribution(),
            "employer_pf": payroll.get_employer_pf_contribution(),
            "withholding_tax": payroll.get_tax_for_taxable_income()["total_tax"],
            "withholding_rent_tax": payroll.get_tax_for_taxable_income()["rent_tax"],
            "benefits_in_kind": payroll.get_benefits_in_kind()["benefit_in_kind"],
            "loan_details": payroll.get_active_loan_deductions(),
        }
        messages.success(request, f"Payslip for {staff.fname} has been generated")        

    context = {
        'staff': staff,
        'company_info': company_info,
        'payroll_data': payroll_data,
        "selected_month": selected_month,
        "selected_year": selected_year,
    }
    return render(request, 'hr/payrol.html', context)



@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('process_all_payroll')
def payroll_processing(request):
    selected_month = request.GET.get("month")
    selected_year = request.GET.get("year")
    all_payrolls = []
    staff_with_missing_salary = []

    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)
        
        # current_month_date = date.fromisoformat(selected_month)
        staff_list = Employee.objects.exclude(companyinformation__active_status='Inactive').order_by('lname')

        for staff in staff_list:
            company_info = CompanyInformation.objects.filter(staffno=staff).first()
            if not company_info:
                continue  # skip if company info is missing

            try:
                payroll = PayrollCalculator(staffno=staff, month=selected_date)
                basic_salary = payroll.get_entitled_basic_salary()

                if basic_salary is None:
                    staff_with_missing_salary.append(f"{staff.fname} {staff.lname}")
                    continue

                payroll_data = {
                    "staff": staff,
                    "company_info": company_info,
                    "month": selected_date.strftime("%B %Y"),
                    "selected_month": selected_month,
                    "selected_year": selected_year,
                    "basic_salary": basic_salary,
                    "total_income": payroll.get_gross_income() - basic_salary,
                    "gross_salary": payroll.get_gross_income(),
                    "pf_employee": payroll.get_pf_contribution(),
                    "income_tax": payroll.get_income_tax(),
                    "total_deduction": payroll.get_total_deductions(),
                    "net_salary": payroll.get_net_salary(),
                    "taxable_income": payroll.get_taxable_income(),
                    "incomes": payroll.get_allowance_values()["incomes"],
                    "deductions": payroll.get_deductions()["deductions"],
                    "ssf_employee": payroll.get_ssnit_contribution(),
                    "employer_ssf": payroll.get_employer_ssnit_contribution(),
                    "employer_pf": payroll.get_employer_pf_contribution(),
                    "withholding_tax": payroll.get_tax_for_taxable_income()["total_tax"],
                    "withholding_rent_tax": payroll.get_tax_for_taxable_income()["rent_tax"],
                    "benefits_in_kind": payroll.get_benefits_in_kind()["benefit_in_kind"],
                }

                all_payrolls.append(payroll_data)

            except (TypeError, InvalidOperation):
                staff_with_missing_salary.append(f"{staff.fname} {staff.lname}")
                continue

        if staff_with_missing_salary:
            staff_names = ", ".join(staff_with_missing_salary)
            messages.error(request, f"The following staff have no basic salary set and were skipped: {staff_names}")

        if all_payrolls:
            messages.success(request, f"Payslips for {selected_date.strftime('%B %Y')} have been generated successfully.")

    context = {
        "payrolls": all_payrolls,
        "selected_month": selected_month,
        "selected_year": selected_year,
    }

    return render(request, "hr/payroll_processing.html", context)


@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('generate_payroll_register')
def payroll_register(request):
    staff_categories = StaffCategory.objects.all().order_by('category_name')
    campus = Campus.objects.all().order_by('campus_name')
    schools = School_Faculty.objects.all().order_by('sch_fac_name')
    departments = Department.objects.all().order_by('dept_long_name')
    banks = Bank.objects.all().order_by('bank_short_name')
    directorate = Directorate.objects.all().order_by('direct_name')
    selected_month = request.GET.get("month")
    selected_staff_cat = request.GET.get("staff_cat", None)
    selected_campus = request.GET.get("campus", None)
    selected_school = request.GET.get("school", None) 
    selected_department = request.GET.get("department", None)
    selected_directorate = request.GET.get("directorate", None)
    selected_bank = request.GET.get("bank", None)    
        
    all_payrolls = []
    filters = Q()

    if selected_month:
        current_month_date = date.fromisoformat(selected_month)
        
        if selected_staff_cat:
            filters &= Q(companyinformation__staff_cat=selected_staff_cat)
            print(selected_staff_cat)
            
        if selected_school:
            filters &= Q(companyinformation__sch_fac_dir=selected_school)
            print(selected_school)
            
        if selected_department:
            filters &= Q(companyinformation__dept=selected_department)
            print(selected_department)
            
        if selected_directorate:
            filters &= Q(companyinformation__directorate=selected_directorate)
            print(selected_directorate)
            
        if selected_bank:
            filters &= Q(companyinformation__bank_name=selected_bank)
            print(selected_bank)
            
        if selected_campus:
            filters &= Q(companyinformation__campus=selected_campus)
            print(selected_campus)
            
            
        staff_list = Employee.objects.filter(filters).exclude(companyinformation__active_status='Inactive').order_by('lname')
        
        print("Staff List", staff_list)
        if not staff_list:
            messages.error(request, "No staff found for the selected criteria.")
            return redirect('payroll-register')

        for staff in staff_list:
            company_info = CompanyInformation.objects.filter(staffno=staff).first()
            if not company_info:
                continue 

            payroll = PayrollCalculator(staffno=staff, month=current_month_date)

            payroll_data = {
                "staff": staff,
                "company_info": company_info,
                "month": current_month_date.strftime("%B %Y"),
                "basic_salary": payroll.get_entitled_basic_salary(),
                "total_income": payroll.get_gross_income() - payroll.get_entitled_basic_salary(),
                "gross_salary": payroll.get_gross_income(),
                "incomes": payroll.get_allowance_values()["incomes"],
                "income_tax": payroll.get_income_tax(),
                "deductions": payroll.get_deductions()["total_deduction"],
                "ssf_employee": payroll.get_ssnit_contribution(),
                "pf_employee": payroll.get_pf_contribution(),
                "employer_pf": payroll.get_employer_pf_contribution(),
                "total_deduction": payroll.get_total_deductions(),
                "net_salary": payroll.get_net_salary(),
            }

            all_payrolls.append(payroll_data)
            
        messages.success(request, f"Payroll Register for {selected_month} has been generated succesfully")
    context = {
        "payrolls": all_payrolls,
        "selected_month": selected_month,
        "staff_categories": staff_categories,
        "campus": campus,
        "schools": schools,
        "departments": departments,
        "banks": banks,
        "directorate":directorate,
        "selected_staff_cat": selected_staff_cat,
        "selected_campus": selected_campus, 
        "selected_school": selected_school,
        "selected_department": selected_department,
        "selected_bank": selected_bank,
        "selected_directorate":selected_directorate,
    }
    return render(request, 'hr/payroll_register.html', context)


@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('export_bank_sheet')
def payroll_bank_sheet(request):
    banks = Bank.objects.all().order_by('bank_short_name')
    selected_month = request.GET.get("month")
    selected_year = request.GET.get("year")
    selected_bank = request.GET.get("bank", None)
    all_payrolls = []
    DEFAULT_EXPORT_FORMAT = ["sort_code","accno","acc_name","narration","bank_name","net_salary","bank_branch",]
    COLUMN_LABELS = {"accno": "Account Number","acc_name": "Account Name","narration": "Narration","bank_name": "Bank Name","sort_code": "Sort Code","net_salary": "Net Salary","bank_branch": "Bank Branch",}
    export_format = DEFAULT_EXPORT_FORMAT
    
    filters = Q()

    if selected_month and selected_year:
        # current_month_date = date.fromisoformat(selected_month)
        selected_date = date(int(selected_year), int(selected_month), 28)
        
        if selected_bank:
            selected_bank = get_object_or_404(Bank, pk=selected_bank)
            filters &= Q(companyinformation__bank_name=selected_bank.bank_short_name)
            if selected_bank.export_format:
                export_format = selected_bank.export_format
            print("Selected Bank:", selected_bank)        
        
        staff_list = Employee.objects.filter(filters).exclude(companyinformation__active_status='Inactive').order_by('lname')
        print("Staff List:", staff_list)
        if not staff_list:
            messages.error(request, "No staff found for the selected criteria.")
            return redirect('payroll-bank-sheet')
        
        for staff in staff_list:
            company_info = CompanyInformation.objects.filter(staffno=staff).first()
            if not company_info:
                continue
            
            branch_name = company_info.bank_branch
            bank_name = company_info.bank_name
            
            sort_code = None
            
            if branch_name and bank_name: 
                branch = BankBranch.objects.filter(branch_name__iexact=branch_name, bank_code__bank_short_name__iexact=bank_name).first()
                if branch:
                    sort_code = branch.sort_code

            payroll = PayrollCalculator(staffno=staff, month=selected_date)

            payroll_data = {
                "staff": staff,
                "company_info": company_info,
                "month": selected_date.strftime("%B %Y"),
                "net_salary": payroll.get_net_salary(),
                "sort_code": sort_code,
                "bank_branch": company_info.bank_branch,
                "bank_name": company_info.bank_name,
                "accno": company_info.accno,
                "acc_name": company_info.acc_name,
                "narration": f"Salary for {selected_date.strftime('%B %Y')}",     
            }

            all_payrolls.append(payroll_data)
            
        messages.success(request, f"Bank Sheet for {selected_date} has been generated succesfully")
    context = {
        "payrolls": all_payrolls,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "selected_bank": selected_bank,
        "export_format": export_format,
        "banks": banks,
        "column_labels": COLUMN_LABELS,
    }
    return render (request, 'hr/payroll_bank_sheet.html', context)


@login_required
@role_required(['superadmin'])
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('modify_salary')
def staff_salary_increment(request):
    staff_categories = StaffCategory.objects.all()
    staff_list = []
    increment_percentage = None
    
    if request.method == 'POST':
        staff_cat = request.POST.get('staff_cat')
        increment_percentage = request.POST.get('increment_percentage')
        selected_staff = request.POST.getlist('selected_staff')
        
        if staff_cat:
            company_infos = CompanyInformation.objects.filter(staff_cat=staff_cat).exclude(active_status='Inactive').select_related('staffno')
            staff_list = [info.staffno for info in company_infos]
            
            
        if increment_percentage and selected_staff:
            increment_percentage = Decimal(increment_percentage)
            print("Selected Staff IDs:", selected_staff)

            for staff_id in selected_staff:
                staff = get_object_or_404(Employee, pk=staff_id) 
                company_info = get_object_or_404(CompanyInformation, staffno=staff) 
                current_salary = Decimal(company_info.salary)
                increment_amount = current_salary * (increment_percentage / 100)
                new_salary = round(current_salary + increment_amount, 2)
                
                company_info.salary = new_salary
                company_info.save()
                
            messages.success(request, f"Salary increment of {increment_percentage}% for staff {selected_staff} applied successfully")
            logger.info(f"Salary increment of {increment_percentage}% applied to selected staff {selected_staff} by {request.user.username}.")
            return redirect('payroll-salary-increment')
            
    context = {
        'staff_categories': staff_categories,
        'staff_list': staff_list,
        'increment_percentage': increment_percentage
    }
    return render(request, 'hr/staff_salary_increment.html', context)

def new_landing(request):
    sch_fac_count = School_Faculty.objects.all().count()
    dept_count = Department.objects.all().count()
    directorate_count = Directorate.objects.all().count()
    unit_count = Unit.objects.all().count()
    staff_category = StaffCategory.objects.all().count()
    bank_count = Bank.objects.all().count()
    bank_branch_count = BankBranch.objects.all().count()
    tax_band_count = TaxBand.objects.all().count()
    
    
    context = {
        "sch_fac_count":sch_fac_count,
        "dept_count":dept_count,
        "directorate_count":directorate_count,
        "unit_count":unit_count,    
        "staff_category":staff_category,
        "bank_count":bank_count,
        "bank_branch_count":bank_branch_count,
        "tax_band_count":tax_band_count,
    }
    return render(request, 'payroll/landing.html', context)




####### REPORT ##########

@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
def payroll_report(request):
    return render(request, "payroll/report.html")


@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('view_loan_history')
def loan_history(request):
    selected_month = request.GET.get("month")
    selected_year = request.GET.get("year")
    staffno = request.GET.get("staffno")
    filter_status = request.GET.get("filter_status", None)
    
    history_data = []
    filters = Q()
    
    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)
        # current_month_date = date.fromisoformat(selected_month)
        filters &= Q(start_date__lte=selected_date, end_date__gte=selected_date)

        if filter_status == "active":
            filters &= Q(is_active=True)
        elif filter_status == "inactive":
            filters &= Q(is_active=False)

        if staffno and staffno != "all":
            filters &= Q(staffno=staffno)

        loans = StaffLoan.objects.filter(filters).order_by('staffno')

        for loan in loans:
            payments = loan.payments.order_by('payment_date')
            
            # Total value of loan (principal + total interest for full duration)
            total_loan = loan.amount + loan.total_interest
            monthly_installment = loan.monthly_installment

            # Actual amount paid up to and including the selected month
            total_paid = loan.payments.filter(
                payment_date__year__lte=selected_date.year,
                payment_date__month__lte=selected_date.month
            ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

            # Estimate how many full months have been paid
            months_paid = int(total_paid / monthly_installment) if monthly_installment > 0 else 0
            months_left = loan.duration_months - months_paid

            # Derive monthly principal and interest portions
            monthly_principal = loan.amount / loan.duration_months
            monthly_interest = loan.total_interest / loan.duration_months

            # Estimate how much of the paid amount went to principal and interest
            principal_paid = months_paid * monthly_principal
            interest_paid = months_paid * monthly_interest

            # Remaining principal and interest balances
            principal_balance = loan.amount - principal_paid
            interest_balance = loan.total_interest - interest_paid

            # Final outstanding = what's left to be paid
            outstanding = principal_balance + interest_balance

            history_data.append({
                "staff": loan.staffno,
                "loan": loan,
                "payments": payments,
                "duration_months": loan.duration_months,
                "months_paid": months_paid,
                "months_left": months_left,
                "monthly_deduction": monthly_installment,
                "total_loan": round(total_loan, 2),
                "total_paid": round(total_paid, 2),
                "principal": round(loan.amount, 2),
                "principal_paid": round(principal_paid, 2),
                "principal_balance": round(principal_balance, 2),
                "total_principal": round(loan.amount, 2),
                "total_interest": round(loan.total_interest, 2),
                "interest_paid": round(interest_paid, 2),
                "interest_balance": round(interest_balance, 2),
                "outstanding": round(outstanding, 2),
            })


    print("Loan History", history_data)
    
    export_format = request.GET.get("format")
    if export_format == "pdf":
        return render_to_pdf("hr/loan_history.html", {
            "history_data": history_data,
            "report_for": staffno,
        }, filename="loan_history.pdf")

    if export_format == "excel":
        excel_data = {}
        for entry in history_data:
            sheet_title = f"{entry['staff'].fname}_{entry['loan'].loan_type}_{entry['loan'].id}"
            rows = [{
                "Payment Date": p.payment_date,
                "Amount Paid (GH₵)": p.amount_paid,
            } for p in entry["payments"]]

            rows.append({})
            rows.append({"Total Paid": entry["total_paid"]})
            rows.append({"Outstanding": entry["outstanding"]})

            excel_data[sheet_title] = rows

        return render_to_excel(excel_data, filename="loan_history.xlsx")

    return render(request, "hr/loan_history.html", {
        "history_data": history_data,
        "employees": Employee.objects.all(),
        "report_for": staffno,
        "filter_status": filter_status,
        "selected_month": selected_month,
        "selected_year": selected_year,
    })



@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('view_payroll_history')
@role_required(['superadmin'])
def payroll_history(request):
    selected_month = request.GET.get("filter_by_month")
    selected_year = request.GET.get("filter_by_year")
    staffno = request.GET.get("staffno")
    payroll_data = []
    
    if selected_month and selected_year:
        current_month_date = date(int(selected_year), int(selected_month), 28)
        
        if staffno and staffno != "all":
            staff = get_object_or_404(Employee, pk=staffno)
            staff_list = [staff]
        elif staffno == "all":
            staff_list = Employee.objects.all()
        else:
            staff_list = []

        for staff in staff_list:
            payrolls = Payroll.objects.filter(staffno=staff, month=current_month_date)
            # payrolls = Payroll.objects.filter(staffno=staff).order_by('-month')
            for p in payrolls:
                payroll_data.append({
                    "staff": staff,
                    "payroll": p
                })

        export_format = request.GET.get("format")
        
        if export_format == "pdf":
            return render_to_pdf("hr/payroll_history.html", {
                "payroll_data": payroll_data,
                "report_for": staffno,
            }, filename="payroll_history.pdf")

        if export_format == "excel":
            excel_data = {}
            for entry in payroll_data:
                p = entry["payroll"]
                sheet_name = f"{entry['staff'].fname}_{p.month.strftime('%Y-%m')}"
                excel_data[sheet_name] = [{
                    "Month": p.month,
                    "Basic Salary": p.basic_salary or 0,
                    "Total Income": p.total_income or 0,
                    "Gross Salary": p.gross_salary or 0,
                    "Income Tax": p.income_tax or 0,
                    "SSF": p.ssf or 0,
                    "PF Employee": p.pf_employee or 0,
                    "PF Employer": p.pf_employer or 0,
                    "Other Deductions": p.other_deductions or 0,
                    "Total Deduction": p.total_deduction or 0,
                    "Net Salary": p.net_salary or 0,
                    "Cost Center": p.cost_center or "",
                }]

            return render_to_excel(excel_data, filename="payroll_history.xlsx")

    return render(request, "hr/payroll_history.html", {
        "payroll_data": payroll_data,
        "employees": Employee.objects.all(),
        "report_for": staffno,
        "selected_month": selected_month,
        "selected_year": selected_year,
    })
    
    
@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('view_income_history')
def income_history(request):
    selected_month = request.GET.get("filter_by_month")
    selected_year = request.GET.get("filter_by_year")
    staffno = request.GET.get("staffno")
    income_type_id = request.GET.get("income_type")

    income_data = []
    total_amount = 0
    
    statutory_types = ["Basic Salary"]

    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 1)

        # ✅ only allow if payroll for selected month is approved
        if not Payroll.objects.filter(month__year=selected_date.year, month__month=selected_date.month).exists():
            messages.error(request, f"Payroll for {selected_date.strftime('%B %Y')} has not been proccessed")
            return redirect('income-history')
        
        # staff selection
        if staffno and staffno != "all":
            staff_list = [get_object_or_404(Employee, pk=staffno)]
        elif staffno == "all":
            staff_list = Employee.objects.all()
        else:
            staff_list = []

        for staff in staff_list:
            if not Payroll.objects.filter(staffno=staff, month__year=selected_date.year, month__month=selected_date.month).exists():
                continue
            
            incomes = StaffIncome.objects.filter(staffno=staff)
            
            if income_type_id and income_type_id != "all":
                if income_type_id not in statutory_types:
                    incomes = incomes.filter(income_type=income_type_id)
                else:
                    incomes = incomes.filter(income_type=income_type_id)
                
            for income in incomes:
                start = income.start_month
                end = income.end_month or selected_date
                if start <= selected_date <= end:
                    income_data.append({
                        "staff": staff,
                        "income_type": str(income.income_type),
                        "amount": income.amount or 0,
                        "for_month": selected_date,
                    })
                    
            payroll = Payroll.objects.filter(staffno=staff, month__year=selected_date.year, month__month=selected_date.month).first()
            if payroll:
                payroll_income = [("Basic Salary", payroll.basic_salary)]
                
                for itype, amount in payroll_income:
                    if amount and (income_type_id == "all" or not income_type_id or itype == income_type_id):
                        income_data.append({
                            "staff": staff,
                            "income_type": itype,
                            "amount": amount,
                            "for_month": selected_date,
                        })
         
        total_amount = sum(entry["amount"] for entry in income_data)
        # Export PDF/Excel
        export_format = request.GET.get("format")
        if export_format and income_data:
            filename = f"{income_type_id.replace(' ', '_')}__{selected_date.strftime('%b_%Y')}"
            if export_format == "pdf":
                context = {
                    "income_data": income_data,
                    "total_amount": total_amount,
                    "selected_date": selected_date.strftime('%B %Y'),
                }
                return render_to_pdf("export/incomes.html", context, f"{filename}.pdf")

            if export_format == "excel":
                rows = []
                for entry in income_data:
                    rows.append({
                        "Employee ID": entry["staff"].staffno,
                        "Employee": f"{entry['staff'].fname} {entry['staff'].lname} {entry['staff'].middlenames}",
                        "Income Type": entry["income_type"],
                        # "Month": entry["for_month"].strftime("%B %Y"),
                        "Amount": entry["amount"],
                    })
                return render_to_excel({"Income History": rows}, f"{filename}.xlsx")
                       
    context = {
        "income_data": income_data,
        "employees": Employee.objects.all(),
        "income_types": list(IncomeType.objects.values_list("name", flat=True)),
        "statutory_incomes": statutory_types,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "report_for": staffno,
        "selected_income_type": income_type_id,
        "total_amount": total_amount,
    }
                    
    return render(request, "hr/income_history.html", context)


@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('view_deduction_history')
def deduction_history(request):
    selected_month = request.GET.get("filter_by_month")
    selected_year = request.GET.get("filter_by_year")
    staffno = request.GET.get("staffno")
    deduction_type_id = request.GET.get("deduction_type")

    deduction_data = []
    total_amount = 0

    # 👇 Statutory names
    statutory_types = ["Income Tax", "SSF", "PF Employee", "PF Employer"]

    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)

        if not Payroll.objects.filter(month__year=selected_date.year, month__month=selected_date.month).exists():
            messages.error(request, f"Payroll for {selected_date.strftime('%B %Y')} has not been processed.")
            return redirect('deduction-history')

        if staffno and staffno != "all":
            staff_list = [get_object_or_404(Employee, pk=staffno)]
        elif staffno == "all":
            staff_list = Employee.objects.all()
        else:
            staff_list = []

        for staff in staff_list:
            if not Payroll.objects.filter(staffno=staff, month__year=selected_date.year, month__month=selected_date.month).exists():
                continue

            # 👉 Custom deductions
            deductions = StaffDeduction.objects.filter(staffno=staff)

            if deduction_type_id and deduction_type_id != "all":
                # Only filter custom deductions if not in statutory
                if deduction_type_id not in statutory_types:
                    deductions = deductions.filter(deduction_type=deduction_type_id)
                else:
                    deductions = deductions.filter(deduction_type=deduction_type_id)
            
            for deduction in deductions:
                start = deduction.start_month
                end = deduction.end_month or selected_date
                if start <= selected_date <= end:
                    deduction_data.append({
                        "staff": staff,
                        "deduction_type": str(deduction.deduction_type),
                        "amount": deduction.amount or 0,
                        "for_month": selected_date,
                    })

            # 👉 Statutory
            payroll = Payroll.objects.filter(staffno=staff, month__year=selected_date.year, month__month=selected_date.month).first()
            if payroll:
                payroll_deductions = [
                    ("Income Tax", payroll.income_tax),
                    ("SSF", payroll.ssf),
                    ("PF Employee", payroll.pf_employee),
                    ("PF Employer", payroll.pf_employer),
                ]

                for dtype, amount in payroll_deductions:
                    if amount and (deduction_type_id == "all" or not deduction_type_id or dtype == deduction_type_id):
                        deduction_data.append({
                            "staff": staff,
                            "deduction_type": dtype,
                            "amount": amount,
                            "for_month": selected_date,
                        })
                        
        total_amount = sum(entry["amount"] for entry in deduction_data)
               
        # Export PDF/Excel
        export_format = request.GET.get("format")
        if export_format and deduction_data:
            filename = f"{deduction_type_id.replace(' ', '_')}__{selected_date.strftime('%b_%Y')}"
            if export_format == "pdf":
                context = {
                    "deduction_data": deduction_data,
                    "total_amount": total_amount,
                    "selected_date": selected_date.strftime('%B %Y'),
                }
                return render_to_pdf("export/deductions.html", context, f"{filename}.pdf")
            elif export_format == "excel":
                rows = []
                for entry in deduction_data:
                    rows.append({
                        "Staff No": entry["staff"].staffno,
                        "Staff": f"{entry['staff'].fname} {entry['staff'].lname}",
                        "Deduction Type": entry["deduction_type"],
                        "Month": entry["for_month"].strftime("%B %Y"),
                        "Amount": entry["amount"],
                    })
                return render_to_excel({"Deduction History": rows}, f"{filename}.xlsx")
    
    # Send name lists only
    context = {
        "deduction_data": deduction_data,
        "employees": Employee.objects.all(),
        "deduction_types": list(DeductionType.objects.values_list("name", flat=True)),
        "statutory_deductions": statutory_types,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "report_for": staffno,
        "selected_deduction_type": deduction_type_id,
        "total_amount": total_amount,
    }

    return render(request, "hr/deduction_history.html", context)



@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('view_paye-history')
def paye_history(request):
    selected_month = request.GET.get("filter_by_month")
    selected_year = request.GET.get("filter_by_year")
    staffno = request.GET.get("staffno")
    
    paye_data = []
    
    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 1)

        if not Payroll.objects.filter(month__year=selected_date.year, month__month=selected_date.month).exists():
            messages.error(request, f"Payroll for {selected_date.strftime('%B %Y')} has not been processed.")
            return redirect('paye-history')

        if staffno and staffno != "all":
            staff_list = [get_object_or_404(Employee, pk=staffno)]
        elif staffno == "all":
            staff_list = Employee.objects.all()
        else:
            staff_list = []

        for staff in staff_list:
            if not Payroll.objects.filter(staffno=staff, month__year=selected_date.year, month__month=selected_date.month).exists():
                continue

            payroll = Payroll.objects.filter(staffno=staff, month__year=selected_date.year, month__month=selected_date.month).first()
            if payroll:
                paye_data.append({
                    "staff": staff,
                    "basic_salary": payroll.basic_salary or 0,
                    "paye_total_income": payroll.paye_total_income or 0,
                    "paye_total_emoluments": payroll.paye_total_emoluments or 0,
                    "ssf": payroll.ssf or 0,
                    "pf_employee": payroll.pf_employee or 0,
                    "total_relief": payroll.total_relief or 0,
                    "net_taxable_pay": payroll.net_taxable_pay or 0,
                    "income_tax": payroll.income_tax or 0,
                    "for_month": selected_date,
                })
    
    # Export PDF/Excel
    export_format = request.GET.get("format")
    if export_format and paye_data:
        filename = f"PAYE__{selected_date.strftime('%b_%Y')}"
        if export_format == "pdf":
            context = {
                "paye_data": paye_data,
                "selected_date": selected_date.strftime('%B %Y'),
                "date": datetime.now().strftime("%d %B, %Y")
            }
            return render_to_pdf("export/paye.html", context, f"{filename}.pdf")
        elif export_format == "excel":
            rows = []
            for entry in paye_data:
                rows.append({
                    "Staff No": entry["staff"].staffno,
                    "Staff": f"{entry['staff'].fname} {entry['staff'].lname}",
                    "Basic Salary": entry["basic_salary"],
                    "PAYE Total Income": entry["paye_total_income"],
                    "PAYE Total Emoluments": entry["paye_total_emoluments"],
                    "SSF": entry["ssf"],
                    "PF Employee": entry["pf_employee"],
                    "Total Relief": entry["total_relief"],
                    "Net Taxable Pay": entry["net_taxable_pay"],
                    "Income Tax": entry["income_tax"],
                })
            return render_to_excel({"PAYE History": rows}, f"{filename}.xlsx")
    
    context = {
        "paye_data": paye_data,
        "employees": Employee.objects.all(),
        "selected_month": selected_month,
        "selected_year": selected_year,
        "report_for": staffno,
    }
    
    return render(request, "hr/paye_history.html", context)
