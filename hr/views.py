from math import e
import pprint
from django.http import HttpResponseRedirect, JsonResponse, FileResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse # type: ignore
from .models import *
from django.contrib.auth.models import Group, User, Permission
from setup.models import *
from leave.models import *
from medical.models import *
from django.db.models import Q
from .forms import *
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
from hr.decorators import role_required
from django.db.models.functions import Concat
from django.db.models import F, Value, CharField
from datetime import date
from datetime import timedelta








logger = logging.getLogger('activity')

def parse_date(date_str):
    if not date_str:
        return None 
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected format is YYYY-MM-DD.")


@login_required
def view_logs(request):
    log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'activity.log')
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
        print("Form has been received", form)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            if User.objects.filter(email=email).exists():
                messages.error(request, "Oops, Email address already exists. Please use another email.")
                return redirect('register')
            form.save()
            messages.success(request, f"Account Creation for {username} has been successful")  
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
                if not user.approval:
                    messages.error(request, "Your account is not approved yet. Please contact the administrator.")
                    return render(request, 'authentication/waiting_approval.html')
                login(request, user)
                messages.success(request, f"Login Successful. Welcome Back {user.username}")
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
    # staffs = Employee.objects.order_by('lname').filter()
    staffs = Employee.objects.exclude(companyinformation__active_status='Dormant').order_by('lname')
    active = CompanyInformation.objects.filter(active_status__exact='Active')
    inactive = CompanyInformation.objects.filter(active_status__exact='Inactive')
    staff_count = staffs.count()
    ative_count = active.count()
    inactive_count = inactive.count()
    
    today = timezone.now().date()
    expiring_soon = CompanyInformation.objects.filter(doe__lte=today + timedelta(days=180)).order_by('doe')
    sixty_and_above = Employee.objects.filter(dob__lte=today - timedelta(days=60*365))  # Approximates 60 years
    pending_renewals = RenewalHistorys.objects.filter(is_approved=False, is_disapproved=False)
    pending_promotions = PromotionHistory.objects.filter(is_approved=False, is_disapproved=False)
    pending_users = User.objects.filter(approval=False)
    
    
    notification_count = ( expiring_soon.count() + sixty_and_above.count() + pending_renewals.count() + pending_promotions.count() )

    context = {
        'staffs':staffs,
        'active':active,
        'inactive':inactive,
        'staff_count':staff_count,
        'ative_count':ative_count,
        'inactive_count':inactive_count,
        'expiring_soon':expiring_soon,
        'notification_count':notification_count,
        'pending_renewals':pending_renewals,
        'sixty_and_above':sixty_and_above,
        'pending_promotions':pending_promotions,
        'pending_users':pending_users,
    }
    
    return render(request,'hr/landing_page.html', context)


def topnav_view(request):
    # Get all contracts expiring in the next month
    today = timezone.now().date()
    expiring_soon = CompanyInformation.objects.filter(doe__lte=today + timedelta(days=30)).order_by('doe')

    return render(request, 'partials/_topnav.html', {'expiring_soon': expiring_soon})

def search(request):
    if request.method == 'POST' and 'search' in request.POST:
        staffs = Employee.objects.all()
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
    #     staffpix = "{{ staff.staff_pix.url }}"
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("UPDATE hr_employee SET active_status = 'Inactive' WHERE staffno = %s", [staffno])
            return render(request,'hr/new_staff.html',{'staff':staff,'staffs':staffs,'staff_count':staff_count})
    return render(request, 'delete.html',{'obj':staff1,'staff':staff})


@login_required
def staff_details(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    schools = School.objects.order_by('school_name')
    company_info = CompanyInformation.objects.get(staffno=staff)
    return render(request,'hr/staff_data.html',{'staff':staff,'schools':schools, 'company_info':company_info})

@login_required
@role_required(['superadmin'])
def edit_staff(request,staffno):
    submitted = False
    staffs = Employee.objects.order_by('lname').filter() 
    staff_count = staffs.count()
    title = Title.objects.all()
    staffcategory = StaffCategory.objects.all()
    qualification = Qualification.objects.all()
    staff = Employee.objects.get(pk=staffno)
    form = EmployeeForm(request.POST or None,request.FILES or None,instance=staff)
    if request.method == 'POST':
        if form.is_valid():
            if form.has_changed():
                fname = form.cleaned_data['fname']
                lname = form.cleaned_data['lname']

                print("Form was submitted successfully")
                form.save()
                full_name = f"{fname} {lname}"
                messages.success(request, f"Staff data for {full_name} has been updated successfully")
                logger.info(f"Personal information updated for {full_name} by {request.user.username}")
            else: 
                messages.warning(request, "No changes were made to the staff record.")
            return redirect('staff-details', staffno)
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
    staffs = Employee.objects.filter(filters).exclude(companyinformation__active_status='Dormant').order_by('fname')
    staff_count = staffs.count()
    company_info = CompanyInformation.objects.all()

    # Pagination
    paginator = Paginator(staffs, 10)
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
def dormant_staff(request): 
    staffs = Employee.objects.filter(companyinformation__active_status='Dormant').order_by('lname')
    staff_count = staffs.count()
    company_info = CompanyInformation.objects.all()
        
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
# @role_required(['superadmin'])
def test(request): 
    # Initial querysets for staff, company info, and school
    staffs = Employee.objects.all()
    company_info = CompanyInformation.objects.all()
    staff_school = Staff_School.objects.all()
    
    
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

    # Initial filter container
    filters = Q()

    if request.method == 'POST':
        # Retrieve filter values from POST request
        filter_staffcategory = request.POST.get('filter_staffcategory')
        filter_qualification = request.POST.get('filter_qualification')
        filter_title = request.POST.get('filter_title')
        filter_contract = request.POST.get('filter_contract')
        filter_status = request.POST.get('filter_status')
        filter_gender = request.POST.get('filter_gender')
        filter_department = request.POST.get('filter_department')
        filter_jobtitle = request.POST.get('filter_jobtitle')
        filter_directorate = request.POST.get('filter_directorate')
        filter_school_faculty = request.POST.get('filter_school_faculty')
        filter_age = request.POST.get('filter_age')
        filter_renewal = request.POST.get('filter_renewal')
        filter_promotion = request.POST.get('filter_promotion')

        # Filter by Staff Category
        if filter_staffcategory:
            filters &= Q(companyinformation__staff_cat=filter_staffcategory)

        # Filter by Contract Type
        if filter_contract:
            filters &= Q(companyinformation__contract=filter_contract)

        # Filter by Qualification
        if filter_qualification:
            qualification_filter = Q(heq=filter_qualification) | Q(staff_school__certification=filter_qualification)
            filters &= qualification_filter

        # Filter by Title
        if filter_title:
            filters &= Q(title=filter_title)

        # Filter by Gender
        if filter_gender:
            filters &= Q(gender=filter_gender)

        # Filter by Status
        if filter_status:
            company_info = CompanyInformation.objects.filter(active_status=filter_status)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)

        # Filter by Department
        if filter_department:
            company_info = CompanyInformation.objects.filter(dept=filter_department)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)

        # Filter by Job Title
        if filter_jobtitle:
            company_info = CompanyInformation.objects.filter(job_title=filter_jobtitle)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)
            
        # Filter by Directorate
        if filter_directorate:
            company_info = CompanyInformation.objects.filter(directorate=filter_directorate)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)
            
        # Filter by School/Faculty
        if filter_school_faculty:
            company_info = CompanyInformation.objects.filter(sch_fac_dir=filter_school_faculty)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)
            
        # # Filter by Age
        # if filter_age:
        #     age_range = AGE_CLASSIFICATIONS.get(filter_age)
        #     if age_range:
        #         current_date = date.today()
        #         start_date = current_date - timedelta(days=age_range[1] * 365)
        #         end_date = current_date - timedelta(days=age_range[0] * 365)
        #         filters &= Q(dob__range=(start_date, end_date))
        
        # # Apply custom age range filter
        # if filter_age == "custom" and min_age and max_age:
        #     min_age = int(min_age)
        #     max_age = int(max_age)
        #     if 0 <= min_age <= 999 and 0 <= max_age <= 999:
        #         current_date = date.today()
        #         start_date = current_date - timedelta(days=max_age * 365)
        #         end_date = current_date - timedelta(days=min_age * 365)
        #         filters &= Q(dob__range=(start_date, end_date))
                
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
            renewal_staffno = {renewal.staffno_id for renewal in RenewalHistorys.objects.all()}
            filters &= Q(staffno__in=renewal_staffno)
            
        # Filter by Promotion History
        if filter_promotion == "true":
            promotion_staffno = {promotion.staffno_id for promotion in PromotionHistory.objects.all()}
            filters &= Q(staffno__in=promotion_staffno)

        # Apply filters to the staff queryset
        staffs = staffs.filter(filters).distinct()  # Ensure distinct entries

    # Pagination setup
    paginator = Paginator(staffs, 10)
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
        'filter_age': filter_age,
        'min_age': min_age,
        'max_age': max_age,
        'filter_renewal': filter_renewal,
        'filter_promotion': filter_promotion,
        'renewal_staffno': {renewal.staffno_id for renewal in RenewalHistorys.objects.all()},
    }

    # Render the page
    return render(request, 'hr/test.html', context)


@login_required
@role_required(['superadmin'])
def newstaff(request):
    submitted = False
    staffs = Employee.objects.order_by('lname').filter()
    title = Title.objects.all()
    qualification = Qualification.objects.all()
    staffcategory = StaffCategory.objects.all()
    staff_count = staffs.count()
    
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        print("Form has been received")

        if form.is_valid():
            staff_number = form.cleaned_data['staffno']
            fname = form.cleaned_data['fname']
            lname = form.cleaned_data['lname']

            # Check if staffno already exists
            if Employee.objects.filter(staffno=staff_number).exists():
                full_name = f"{fname} {lname}"
                messages.error(request, f"Staff number {staff_number} for {full_name} already exists. Please use another unique staff number.")
                print(f"Staff number {staff_number} already exists")
            else:
                print("Form was submitted successfully")
                form.save()
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
               'RBA':[(q.name, q.name)  for q in ChoicesRBA.objects.all()],
               'STAFFLEVEL': ChoicesStaffLevel.objects.all().values_list("name", "name"),
               'STAFFSTATUS':[(q.name, q.name)  for q in ChoicesStaffStatus.objects.all()],
               'GENDER': ChoicesGender.objects.all().values_list("name", "name"),
               'DEPENDANTS':[(q.name, q.name)  for q in ChoicesDependants.objects.all()],
               'qualification':qualification,
               'HPQ':[(q.name, q.name)  for q in ChoicesHPQ.objects.all()],
               'REGION':[(q.name, q.name)  for q in ChoicesRegion.objects.all()],
               'title':title,
               'staffcategory':staffcategory,
               'qualification':qualification,
               'MARITALSTATUS': ChoicesMaritalStatus.objects.all().values_list("name", "name"),
               'IDTYPE': ChoicesIdType.objects.all().values_list("name", "name"),
               'DENOMINATION': ChoicesDenomination.objects.all().values_list("name", "name"),
               'RELIGION': ChoicesReligion.objects.all().values_list("name", "name"),
               'SUFFIX':[(q.name, q.name)  for q in ChoicesSuffix.objects.all()]
            }
    return render(request,'hr/new_staff.html',context)


def get_bank_branches(request, bank_name):
    try:
        bank = Bank.objects.get(bank_short_name=bank_name)  # Find bank by name
        branches = BankBranch.objects.filter(bank_code=bank)  # Get branches associated with this bank
        branch_data = [{"branch_name": branch.branch_name} for branch in branches]
        return JsonResponse({"branches": branch_data})
    except Bank.DoesNotExist:
        return JsonResponse({"branches": []}, status=404)


def get_departments(request, sch_name):
    try:
        school_faculty = School_Faculty.objects.get(sch_fac_name=sch_name)  
        departments = Department.objects.filter(sch_fac=school_faculty) # Get departments associated with this school/faculty
        department_data = [{"dept_long_name": dept.dept_long_name} for dept in departments]
        return JsonResponse({"departments": department_data})
    except School_Faculty.DoesNotExist:
        return JsonResponse({"departments": []}, status=404)
    
    
@login_required
@role_required(['superadmin'])
def company_info(request,staffno):
    submitted = False
    company_infos = CompanyInformation.objects.filter(staffno__exact=staffno)    
    staff = Employee.objects.get(pk=staffno)
    staffcategory = StaffCategory.objects.all()
    contract = Contract.objects.all()
    # company_info_count = company_infos.count()
    campus = Campus.objects.all()
    school_faculty = School_Faculty.objects.all()
    directorate = Directorate.objects.all()
    bank_list = Bank.objects.all()
    bankbranches = BankBranch.objects.all()
    departments = Department.objects.all()
    jobtitle = JobTitle.objects.all()
    
    
    if request.method == 'POST':
        form = CompanyInformationForm(request.POST, request.FILES)
        # print(form)
        print("form has been recieved")
        if form.is_valid(): 
            print("form was submitted successfully")
            company_info = form.save(commit=False)
            company_info.staffno = staff 
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
        'contract':contract,
        'campus':campus,
        'bank_list':bank_list,
        'bankbranches':bankbranches,
        'school_faculty':school_faculty,
        'directorate':directorate,
        'RBA':[(q.name, q.name)  for q in ChoicesRBA.objects.all()],
        'STAFFLEVEL': ChoicesStaffLevel.objects.all().values_list("name", "name"),
        'STAFFSTATUS':[(q.name, q.name)  for q in ChoicesStaffStatus.objects.all()],
        'DEPENDANTS':[(q.name, q.name)  for q in ChoicesDependants.objects.all()],
        'departments':departments,
        'jobtitle':jobtitle,
    }
    return render(request,'hr/company_info.html',context)

@login_required
@role_required(['superadmin'])
def edit_company_info(request,staffno):
    company_infos = CompanyInformation.objects.all()  
    company_info = CompanyInformation.objects.get(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    staffcategory = StaffCategory.objects.all()
    contract = Contract.objects.all()
    company_info_count = company_infos.count()
    campus = Campus.objects.all()
    school_faculty = School_Faculty.objects.all()
    directorate = Directorate.objects.all()
    bank_list = Bank.objects.all()
    bankbranches = BankBranch.objects.all()
    departments = Department.objects.all()
    jobtitle = JobTitle.objects.all()

    
    if request.method == 'POST':
        form = CompanyInformationForm(request.POST, request.FILES, instance=company_info)
        if form.is_valid():
            if form.has_changed():
                print("Form was submitted successfully")
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
               'STAFFSTATUS':[(q.name, q.name)  for q in ChoicesStaffStatus.objects.all()],
               'GENDER': ChoicesGender.objects.all().values_list("name", "name"),
               'SUFFIX': ChoicesSuffix.objects.all().values_list("name", "name"),
               'REGION': ChoicesRegion.objects.all().values_list("name", "name"),
               'DEPENDANTS':DEPENDANTS,
               'HPQ':[(q.name, q.name)  for q in ChoicesHPQ.objects.all()],               
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
            }

    return render(request, 'hr/company_info.html', context)

############### EMPLOYEE RELATIONSHIP ###############

@login_required
@role_required(['superadmin'])
def emp_relation(request,staffno):
    submitted = False
    emp_relations = Kith.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    
    if request.method == 'POST':
        form = KithForm(request.POST)
        print("form has been recieved")
        if form.is_valid(): 
            new_percentage = form.cleaned_data['percentage']
            current_total = sum(emp.percentage for emp in emp_relations)
            
            if current_total + new_percentage > 100:
                messages.error(request, 'Total percentage exceeds 100%. Please adjust the percentage.')
            else:
                emp_relation = form.save(commit=False)
                emp_relation.staffno = staff
                emp_relation.save()
                full_name = f"{staff.fname} {staff.lname}"
                messages.success(request, f"Beneficiaries for {full_name} has been created successfully")
                logger.info(f"Beneficiaries added for {full_name} by {request.user.username}")
                return redirect('emp-relation', staffno)
    else:
        form = KithForm
        if 'submitted' in request.GET:
            submitted = True
    context = {
               'form':form,
               'submitted':submitted,
               'emp_relations':emp_relations,
               'staff':staff,
               'RELATIONSHIP': ChoicesDependants.objects.all().values_list("name", "name"),
               'STATUS': ChoicesRelationStatus.objects.all().values_list("name", "name"),
               'GENDER': ChoicesGender.objects.all().values_list("name", "name"),
                'total_percentage': sum(emp.percentage for emp in emp_relations),
            }
    return render(request,'hr/emp_relation.html',context)

@login_required
@role_required(['superadmin'])
def edit_emp_relation(request,staffno,emp_id):
    emp_relations = Kith.objects.filter(staffno__exact=staffno)  
    emp_relation = Kith.objects.get(pk=emp_id)
    staff = Employee.objects.get(pk=staffno)
    emp_count = emp_relations.count()
    form = KithForm(request.POST or None,instance=emp_relation)

    if request.method == 'POST':
        form = KithForm(request.POST, instance=emp_relation)
        if form.is_valid():
            if form.has_changed():
                form.save()
                full_name = f"{staff.fname} {staff.lname}"
                messages.success(request, f"Employee Beneficiaries for {full_name} has been updated successfully")
                logger.info(f"Employee Beneficiaries updated for {full_name} by {request.user.username}")
            return redirect('emp-relation', staffno=staffno)
        
    context = {
                'form':form,
                'emp_relations':emp_relations,
                'emp_relation':emp_relation,
                'staff':staff,
                'emp_count':emp_count,
                'RELATIONSHIP': ChoicesDependants.objects.all().values_list("name", "name"),
               'STATUS': ChoicesRelationStatus.objects.all().values_list("name", "name"),
                'GENDER': ChoicesGender.objects.all().values_list("name", "name"),
               }

    return render(request, 'hr/emp_relation.html', context)

@login_required
@role_required(['superadmin'])
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
@role_required(['superadmin'])
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
                            
                            # print(f"Employee: {employee}")
                            print(f"Created")
                            
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
                                    'salary': row.get('salary', ''),
                                    'cost_center': dept_long_instance,
                                    'bank_name': bank_instance,
                                    'bank_branch': branch_instance, 
                                    'accno': row.get('accno', ''),
                                    'ssn_con': row.get('ssn_con', ''),
                                    'pf_con': row.get('pf_con', ''),
                                }
                            )
                            # print(f"Company Information: {company_info}")
                            success_count += 1
                        except Exception as row_error:
                            transaction.savepoint_rollback(savepoint)
                            errors.append(f"Error in row {reader.line_num}: {row_error}")
                            continue
                        finally:
                            transaction.savepoint_commit(savepoint)

                # Report success and any errors
                if success_count:
                    messages.success(request, f'Successfully uploaded {success_count} records.')
                    logger.info(f"Successfully uploaded {success_count} records by {request.user.username}")
                
                if duplicates:
                    duplicate_message = ', '.join(duplicates)
                    messages.warning(request, f'Duplicate entries found for the following staff members: {duplicate_message}')
                
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
@role_required(['superadmin'])
def education(request,staffno):
    submitted = False
    educations = Staff_School.objects.filter(staffno__exact=staffno)
    staff = Employee.objects.get(pk=staffno)
    qualification = Qualification.objects.all()
    school = School.objects.all()
    school_list = School.objects.order_by('school_name')

    
    if request.method == 'POST':
        form = StaffSchoolForm(request.POST)
        print("form has been recieved")
        if form.is_valid(): 
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
@role_required(['superadmin'])
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
@role_required(['superadmin'])
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
@role_required(['superadmin'])
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
@role_required(['superadmin'])
def medical_transaction(request, staffno):
    submitted = False
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = get_object_or_404(CompanyInformation, staffno=staff)
    medical_entitlement = MedicalEntitlement.objects.filter(staff_cat=company_info.staff_cat).first()
    medical_transactions = Medical.objects.filter(staffno__exact=staffno)
    medical_trans_count = medical_transactions.count()
    academic_years = AcademicYear.objects.all()
    hospitals = Hospital.objects.all()
    
    # Filter beneficiaries based on staffno
    bene_list = Kith.objects.filter(staffno=staff).annotate(full_name=Concat( F('kith_fname'), Value(' '), F('kith_middlenames'), Value(' '), F('kith_lname'), output_field=CharField())).values_list('id', 'full_name')
    
    # Add the staff name to the list
    staff_fullname = f"{staff.title} {staff.fname} {staff.lname}"  # Update field names as per your Employee model
    final_bene_list = list(bene_list) + [(staff.staffno, staff_fullname)]
    # pprint.pprint(final_bene_list)

    
    if not medical_entitlement:
        messages.error(request, 'No medical entitlement found for this staff category.')
        return redirect('medical-entitlement')
    
    remaining_amount = medical_entitlement.get_remaining_amount(staff)
    amount_spent = medical_entitlement.get_amount_used(staff)
    staff_fullname = f"{staff.title} {staff.fname} {staff.lname}"
    
    if request.method == 'POST':
        form = MedicalTransactionForm(request.POST)
        if form.is_valid():
            treatment_cost = int(form.cleaned_data['treatment_cost'])
            academic_year = form.cleaned_data['academic_year']

            medical_transaction = form.save(commit=False)
            medical_transaction.staffno = staff
            medical_transaction.staff_cat = request.POST.get('staff_cat')
            
            if remaining_amount >= treatment_cost:
                medical_transaction.academic_year = academic_year
                medical_transaction.save()

                messages.success(request, f'Medical transaction created successfully  {staff_fullname}.')
                logger.info(f'Medical transaction created successfully for {staff_fullname} by {request.user.username}')
                return redirect('medical-transaction', staffno=staffno)
            else:
                messages.error(request, 'Insufficient Medical balance to process this request. Please review the treatment cost entered')
        else:
            print(form.errors)
            messages.error(request, 'Form is not valid. Please check the entered data.')
            return redirect('medical-transaction', staffno=staffno)
    else:
        form = MedicalTransactionForm()
        if 'submitted' in request.GET:
            submitted = True
            
    context = {
        'form':form,
        'staff':staff,
        'submitted':submitted,
        'medical_entitlement':medical_entitlement,
        'medical_transactions':medical_transactions,
        'remaining_amount':remaining_amount,
        'amount_spent':amount_spent,
        'medical_trans_count':medical_trans_count,
        'company_info':company_info,
        'academic_years':academic_years,
        'hospitals':hospitals,
        'RELATIONSHIP': ChoicesDependants.objects.all().values_list("name", "name"),
        'MEDICALTREATMENT': ChoicesMedicalTreatment.objects.all().values_list("name", "name"),
        'MEDICALTYPE': ChoicesMedicalType.objects.all().values_list("name", "name"),
        'BENE': final_bene_list,
    }
    return render(request, 'hr/medical.html', context)


@login_required
def edit_medical_transaction(request, staffno, med_id):
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = get_object_or_404(CompanyInformation, staffno=staff)
    academic_years = AcademicYear.objects.all()
    medical_transactions = Medical.objects.filter(staffno__exact=staffno)
    medical_transaction = get_object_or_404(Medical, pk=med_id)
    medical_entitlement = MedicalEntitlement.objects.filter(staff_cat=company_info.staff_cat).first()
    hospitals = Hospital.objects.all()
    
    # Filter beneficiaries based on staffno
    bene_list = Kith.objects.filter(staffno=staff).annotate(full_name=Concat( F('kith_fname'), Value(' '), F('kith_middlenames'), Value(' '), F('kith_lname'), output_field=CharField())).values_list('full_name', 'full_name')
    
    # Add the staff name to the list
    staff_fullname = f"{staff.title} {staff.fname} {staff.lname}"  # Update field names as per your Employee model
    final_bene_list = list(bene_list) + [(staff_fullname, staff_fullname)]

    # Calculate the remaining Medical Balance
    remaining_amount = medical_entitlement.get_remaining_amount(staff)
    remaining_amount += medical_transaction.treatment_cost
    form = MedicalTransactionForm(request.POST or None, instance=medical_transaction)
    staff_fullname = f"{staff.title} {staff.fname} {staff.lname}"
    if request.method == 'POST':
        if form.is_valid():
            treatment_cost = int(form.cleaned_data['treatment_cost'])

            if remaining_amount >= treatment_cost:
                form.save()
                messages.success(request, f'Medical transaction updated successfully for {staff_fullname}.')
                return redirect('medical-transaction', staffno=staffno)
            else:
                messages.error(request, 'Insufficient Medical balance to process this request. Please review the treatment cost entered')

    context = {
        'staff': staff,
        'staff_cat': company_info.staff_cat,
        'medical_transactions': medical_transactions,
        'medical_transaction': medical_transaction,
        'form': form,
        'company_info': company_info,
        'LEAVE_TYPE': ChoicesLeaveType.objects.all().values_list("name", "name"),
        'academic_years': academic_years,
        'medical_entitlement': medical_entitlement,
        'remaining_amount': remaining_amount,
        'hospitals': hospitals,
        'RELATIONSHIP': ChoicesDependants.objects.all().values_list("name", "name"),
        'MEDICALTREATMENT': ChoicesMedicalTreatment.objects.all().values_list("name", "name"),
        'MEDICALTYPE': ChoicesMedicalType.objects.all().values_list("name", "name"),
        'BENE': final_bene_list,        
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
@role_required(['superadmin'])
def add_renewal_history(request, staffno):
    submitted = False
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = get_object_or_404(CompanyInformation, staffno=staff)
    renewal_list = RenewalHistorys.objects.filter(staffno=staff)
    renewal_count = renewal_list.count()
    staffcategory = StaffCategory.objects.all()
    jobtitle = JobTitle.objects.all()

    
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
        'company_info':company_info,
    }
    
    return render(request, 'hr/renewal.html', context)


# View for approving a renewal history
@login_required
@role_required(['superadmin'])
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
@role_required(['superadmin'])
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
@role_required(['superadmin'])
def add_promotion_history(request, staffno):
    submitted = False
    staff = get_object_or_404(Employee, pk=staffno)
    company_info = get_object_or_404(CompanyInformation, staffno=staff)
    promotion_list = PromotionHistory.objects.filter(staffno=staff)
    promotion_count = promotion_list.count()
    staffcategory = StaffCategory.objects.all()
    jobtitle = JobTitle.objects.all()


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
        'company_info':company_info,
    }

    return render(request, 'hr/promotion.html', context)

# View for approving a promotion history
@login_required
@role_required(['superadmin'])
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
@role_required(['superadmin'])
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


# payroll information from company info model 
@login_required
@role_required(['superadmin'])
def payroll_details(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    context = {'staff':staff,'company_info':company_info,}
    return render(request, 'hr/payrol.html', context)


@login_required
@role_required(['superadmin'])
def staff_settings(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    
    context = {
        'staff': staff,
        'company_info':company_info,    
    }
    return render(request, 'hr/staff_settings.html', context)
        
@login_required
def mark_dormant(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    full_name = f"{staff.title} {staff.fname} {staff.lname}"
    print(company_info.active_status)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'dormant':
            company_info.active_status = 'Dormant'
            messages.success(request, f"{full_name} marked as Dormant.")
            logger.info(f"{request.user.username} marked {full_name} as Dormant.")
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
@role_required(['superadmin'])
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
    return redirect('assign-user-group')


@login_required
@role_required(['superadmin'])
def disapprove_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, f"User {user.username} has been disapproved!")
    logger.info(f"User {user.username} has been disapproved by {request.user.username}.")
    return redirect('landing')