from math import e
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse # type: ignore
from .models import *
from setup.models import *
from leave.models import *
from django.db.models import Q
from .forms import *
from django.db import connection # type: ignore
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django_otp.plugins.otp_totp.models import TOTPDevice
from two_factor.utils import default_device
import csv
from django.db import transaction
from django.utils import timezone
import logging
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)

def parse_date(date_str):
    if not date_str:
        return None 
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected format is YYYY-MM-DD.")



def index(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # if user.approval:
            login(request, user)
            return redirect('landing')
            # else:
            #     messages.error(request, 'Account not approved yet.', extra_tags='alert alert-warning')
            #     return redirect('login')
        else:
            messages.error(request, 'Invalid login credentials.', extra_tags='alert alert-warning')
            return redirect('login')
    
    return render(request, 'authentication/login.html',{})


def register(request):
    form = RegistrationForm()
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.staffno = form.cleaned_data.get('staffno')
            user.save()

            username = form.cleaned_data.get('username')
            messages.success(request, f'Registration successful for {username}', extra_tags='alert alert-success')  
            return redirect('login')
        else:
            print(form.errors)
            messages.error(request, 'Error in creating account.', extra_tags='alert alert-warning')
    
    context = {'form': form}
    return render(request, 'authentication/register.html', context)


def logoutUser(request):
    logout(request)
    return redirect('login')
    

@login_required(login_url='login')
def landing(request):
    staffs = Employee.objects.order_by('lname').filter()
    active = CompanyInformation.objects.filter(active_status__exact='Active')
    leave = CompanyInformation.objects.filter(active_status__exact='Leave')
    staff_count = staffs.count()
    ative_count = active.count()
    leave_count = leave.count()
    
    today = timezone.now().date()
    expiring_soon = CompanyInformation.objects.filter(doe__lte=today + timedelta(days=30)).order_by('doe')

    context = {
        'staffs':staffs,
        'active':active,
        'leave':leave,
        'staff_count':staff_count,
        'ative_count':ative_count,
        'leave_count':leave_count,
        'expiring_soon':expiring_soon,
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


def staff_details(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    schools = School.objects.order_by('school_name')
    company_info = CompanyInformation.objects.get(staffno=staff)
    return render(request,'hr/staff_data.html',{'staff':staff,'schools':schools, 'company_info':company_info})

def edit_staff(request,staffno):
    staffs = Employee.objects.order_by('lname').filter() 
    staff_count = staffs.count()
    title = Title.objects.all()
    staffcategory = StaffCategory.objects.all()
    qualification = Qualification.objects.all()
    staff = Employee.objects.get(pk=staffno)
    form = EmployeeForm(request.POST or None,request.FILES or None,instance=staff)
    if request.method == 'POST':
        # form = EmployeeForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            full_name = f"{staff.fname} {staff.lname}"
            messages.success(request, f"Staff data for {full_name} has been updated successfully")
            return redirect('staff-details', staffno)
        
    context = {
                'form':form,
            #    'submitted':submitted,
               'staffs':staffs,
               'staff_count':staff_count,
               'RBA':RBA,
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
    return render(request, 'hr/new_staff.html', context)


# Write a filtering query set for 


def allstaff(request): 
    staffs = Employee.objects.order_by('fname')
    staff_count = staffs.count()
    staffcategory = StaffCategory.objects.all()
    company_info = CompanyInformation.objects.all()
    qualification = Qualification.objects.all()
    title = Title.objects.all()
    contract = Contract.objects.all()
    staff_school = Staff_School.objects.all()

    if request.method == 'POST':
        filter_staffcategory = request.POST.get('filter_staffcategory')
        filter_qualification = request.POST.get('filter_qualification')
        filter_title = request.POST.get('filter_title')
        filter_contract = request.POST.get('filter_contract')
        filter_status = request.POST.get('filter_status')
        filter_gender = request.POST.get('filter_gender')
        
        # Initial queryset for filtering
        staffs = Employee.objects.all()
        company_info = CompanyInformation.objects.all()
        staff_school = Staff_School.objects.all()        
        
        # Filter by staff category
        if filter_staffcategory:
            try:
                # Try to get the StaffCategory instance based on the provided name
                staff_category = StaffCategory.objects.get(category_name=filter_staffcategory)
                # Use the StaffCategory instance to filter CompanyInformation
                company_info = company_info.filter(staff_cat=staff_category)
                company_staffno = {company.staffno_id for company in company_info}
                staffs = staffs.filter(staffno__in=company_staffno)
            except StaffCategory.DoesNotExist:
                # Handle the case where the StaffCategory is not found
                staffs = staffs.none()

        # Filter by Contract
        if filter_contract:
            company_info = CompanyInformation.objects.filter(contract=filter_contract)
            company_staffno = {company.staffno_id for company in company_info}
            staffs = staffs.filter(staffno__in=company_staffno)
            
        if filter_qualification:
            # Filter Employee model
            employee_staffs = staffs.filter(heq=filter_qualification)
            
            # Filter Staff_School model
            filtered_staff_school = staff_school.filter(certification=filter_qualification)
            
            # Get staff numbers from both querysets
            staff_numbers_from_employee = set(employee_staffs.values_list('staffno', flat=True))
            staff_numbers_from_school = set(filtered_staff_school.values_list('staffno', flat=True))
            
            # Combine the staff numbers
            combined_staff_numbers = staff_numbers_from_employee.union(staff_numbers_from_school)
            
            # Filter the staffs queryset based on the combined staff numbers
            staffs = staffs.filter(staffno__in=combined_staff_numbers)    
        
        # Filter by title
        if filter_title:
            staffs = staffs.filter(title=filter_title)
            
        # Filter by title
        if filter_gender:
            staffs = staffs.filter(gender=filter_gender)
            
        # Filter by Staff Staus
        if filter_status:
            company_info = CompanyInformation.objects.filter(active_status=filter_status)
            company_staffno = {company.staffno_id for company in company_info}
            staffs = staffs.filter(staffno__in=company_staffno)

        context = {
            'staffs': staffs,
            'staff_school': staff_school,
            'filter_staffcategory': filter_staffcategory,
            'filter_qualification': filter_qualification,
            'filter_title':filter_title,
            'company_info': company_info,
            'staff_count': staffs.count(),
            'staffcategory': staffcategory,
            'qualification': qualification,
            'title':title,
            'contract':contract,
            'STAFFSTATUS': [(q.name, q.name) for q in ChoicesStaffStatus.objects.all()],
            'GENDER': [(q.name, q.name) for q in ChoicesGender.objects.all()],

        }
        return render(request, 'hr/allstaff.html', context)
    
    context = {
        'staffs': staffs,
        'staff_school': staff_school,
        'staff_count': staff_count,
        'staffcategory': staffcategory,
        'company_info': company_info,
        'qualification': qualification,
        'title': title,
        'contract':contract,
        'STAFFSTATUS': [(q.name, q.name) for q in ChoicesStaffStatus.objects.all()],
        'GENDER': [(q.name, q.name) for q in ChoicesGender.objects.all()],
    }
    return render(request, 'hr/allstaff.html', context)
    

def newstaff(request):
    submitted = False
    staffs = Employee.objects.order_by('lname').filter()
    title = Title.objects.all()
    qualification = Qualification.objects.all()
    staffcategory = StaffCategory.objects.all()
    staff_count = staffs.count()
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        # print(form)
        print("form has been recieved")
        if form.is_valid(): 
            print("form was submitted successfully")
            form.save()
            staff_number = form.cleaned_data['staffno']
            url = reverse('company-info', kwargs={'staffno': str(staff_number)})
            print(url)
            full_name = f"{staff.fname} {staff.lname}"
            messages.success(request, f"Staff data for {full_name} has been updated successfully")
            return HttpResponseRedirect(url)
        else:
            print("form.errors")
            print(form.errors)
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

# function for fetch bank branch using bank id
def get_bank_branches(request, bank_id):
    branches = BankBranch.objects.filter(bank_code_id=bank_id).values('id', 'branch_name')
    return JsonResponse({'branches': list(branches)})

def get_departments(request, sch_fac_id):
    departments = Department.objects.filter(sch_fac_id=sch_fac_id).values('id', 'dept_long_name')
    return JsonResponse({'departments': list(departments)})

def company_info(request,staffno):
    submitted = False
    company_infos = CompanyInformation.objects.filter(staffno__exact=staffno)    
    staff = Employee.objects.get(pk=staffno)
    staffcategory = StaffCategory.objects.all()
    contract = Contract.objects.all()
    # company_info_count = company_infos.count()
    campus = Campus.objects.all()
    department = Department.objects.all()
    school_faculty = School_Faculty.objects.all()
    directorate = Directorate.objects.all()
    bank_list = Bank.objects.all()
    bankbranches = BankBranch.objects.all()
    
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
            messages.success(request, f"Staff data for {full_name} has been updated successfully")
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
               'department':department,
               'bank_list':bank_list,
               'bankbranches':bankbranches,
               'school_faculty':school_faculty,
               'directorate':directorate,
               'RBA':[(q.name, q.name)  for q in ChoicesRBA.objects.all()],
               'STAFFLEVEL': ChoicesStaffLevel.objects.all().values_list("name", "name"),
               'STAFFSTATUS':[(q.name, q.name)  for q in ChoicesStaffStatus.objects.all()],
               'DEPENDANTS':[(q.name, q.name)  for q in ChoicesDependants.objects.all()],
            }
    return render(request,'hr/company_info.html',context)


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
    dept = Department.objects.all()
    
    # Filter bank branches and department based on the selected bank and school from the database
    bankbranches = BankBranch.objects.filter(bank_code_id=company_info.bank_name_id) if company_info.bank_name_id else BankBranch.objects.none()
    departments = Department.objects.filter(sch_fac_id=company_info.sch_fac_dir_id) if company_info.sch_fac_dir_id else Department.objects.none()

    # Pass the selected bank and branch, school/faculty and department IDs to the template
    selected_bank_id = company_info.bank_name_id
    selected_branch_id = company_info.bank_branch_id
    selected_sch_fac_id = company_info.sch_fac_dir_id
    selected_dept_id = company_info.dept_id
    
    if request.method == 'POST':
        form = CompanyInformationForm(request.POST, request.FILES, instance=company_info)
        if form.is_valid():
            form.save()
            full_name = f"{staff.fname} {staff.lname}"
            messages.success(request, f"Staff data for {full_name} has been updated successfully")
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
               'dept':dept,
               'bank_list': bank_list,
                'bank_branches': bankbranches,
                'selected_bank_id': selected_bank_id,
                'selected_branch_id': selected_branch_id,
                'selected_sch_fac_id': selected_sch_fac_id,
                'selected_dept_id': selected_dept_id,
            }

    return render(request, 'hr/company_info.html', context)

############### EMPLOYEE RELATIONSHIP ###############

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
                messages.success(request, f"Staff data for {full_name} has been updated successfully")
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


def edit_emp_relation(request,staffno,emp_id):
    emp_relations = Kith.objects.filter(staffno__exact=staffno)  
    emp_relation = Kith.objects.get(pk=emp_id)
    staff = Employee.objects.get(pk=staffno)
    emp_count = emp_relations.count()
    form = KithForm(request.POST or None,instance=emp_relation)

    if request.method == 'POST':
        form = KithForm(request.POST, instance=emp_relation)
        if form.is_valid():
            form.save()
            full_name = f"{staff.fname} {staff.lname}"
            messages.success(request, f"Staff data for {full_name} has been updated successfully")
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

def delete_emp_relation(request,emp_id,staffno):
    emp_relation = Kith.objects.get(pk=emp_id)
    if request.method == 'GET':
       emp_relation.delete()
    return redirect('emp-relation', staffno)

# END OF EMPLOYEE RELATIONSHIP 



# Write a function for bulk upload csv format
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
                            
                            # If employee already exists, add to duplicates and skip
                            if not created:
                                duplicates.append(f"{row['fname']} {row['lname']}")
                                transaction.savepoint_rollback(savepoint)
                                continue
                            
                            # Continue processing if it's a new employee
                            # Handle Bank instance
                            bank_short_name = row.get('bank_name')
                            bank_instance, created = Bank.objects.get_or_create(bank_short_name=bank_short_name)
                            
                            # Handle BankBranch instance
                            branch_name = row.get('bank_branch')
                            branch_instance, created = BankBranch.objects.get_or_create(branch_name=branch_name, bank_code=bank_instance)
                            
                            # Handle Staff Category instance
                            category_name = row.get('staff_cat')
                            staff_category_instance, created = StaffCategory.objects.get_or_create(category_name=category_name)
                            
                            # Handle Contract instance
                            contract_type = row.get('contract')
                            contract_instance, created = Contract.objects.get_or_create(contract_type=contract_type)
                            
                            # Handle School/Faculty instance
                            sch_fac_name = row.get('sch_fac_dir')
                            sch_fac_instance, created = School_Faculty.objects.get_or_create(sch_fac_name=sch_fac_name)
                            
                            # Process Directorate if available
                            direct_name = row.get('directorate')
                            direct_instance = None
                            if direct_name:
                                direct_instance, created = Directorate.objects.get_or_create(direct_name=direct_name)
                            
                            # Handle Department instance
                            dept_long_name = row.get('dept')
                            dept_long_instance, created = Department.objects.get_or_create(dept_long_name=dept_long_name, sch_fac=sch_fac_instance)
                            
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
                
                if duplicates:
                    duplicate_message = ', '.join(duplicates)
                    messages.warning(request, f'Duplicate entries found for the following staff members: {duplicate_message}')
                
                if errors:
                    error_message = "</p><p>".join(errors)
                    messages.error(request, f"Errors occurred during upload:\n{error_message}")
                    logger.error(f"Upload Errors:\n{error_message}")
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                messages.error(request, f"Error processing file: {e}")
        
    else:
        form = CSVUploadForm()

    return render(request, 'hr/upload.html', {'form': form})




####### EDUCATIONAL BACKGROUND #################
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
            messages.success(request, f"Staff data for {full_name} has been updated successfully")
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
            form.save()
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

def delete_education(request,edu_id,staffno):
    education = Staff_School.objects.get(pk=edu_id)
    if request.method == 'GET':
       education.delete()
    return redirect('education', staffno)


######################################################################
### Staff leave transaction
######################################################################
def leave_transaction(request, staffno):
    submitted = False
    staff = get_object_or_404(Employee, pk=staffno) 
    company_info = get_object_or_404(CompanyInformation, staffno=staff)   
    leave_entitlement = LeaveEntitlement.objects.filter(staff_cat=company_info.staff_cat).first()
    leave_transactions = Staff_Leave.objects.filter(staffno__exact=staffno)
    leave_trans_count = leave_transactions.count()

    if not leave_entitlement:
        messages.error(request, 'No leave entitlement found for this staff category.')
        return redirect('leave-entitlement')

    remaining_days = leave_entitlement.get_remaining_days(staff)
        
    if request.method == 'POST':
        print("Form submitted")
        form = LeaveTransactionForm(request.POST)
        if form.is_valid():
            days_taken = int(form.cleaned_data['days_taken'])
            academic_year = form.cleaned_data['academic_year']
            
            leave_transaction = form.save(commit=False)
            leave_transaction.staffno = staff
            leave_transaction.staff_cat_id = request.POST.get('staff_cat')
            
            if remaining_days >= days_taken:
                leave_transaction.academic_year = academic_year
                leave_transaction.save()
                
                messages.success(request, 'Leave transaction created successfully.')
                return redirect('leave-transaction', staffno=staffno)
            else:
                messages.error(request, 'Not enough leave entitlement remaining.')
        else:
            print(form.errors)

    else:
        form = LeaveTransactionForm()
        if 'submitted' in request.GET:
            submitted = True

    return render(request, 'hr/leave.html', {
        'staff': staff,
        'staff_cat': company_info.staff_cat,
        'leave_entitlement': leave_entitlement,
        'leave_transactions': leave_transactions,
        'form': form,
        'company_info': company_info,
        'LEAVE_TYPE': ChoicesLeaveType.objects.all().values_list("name", "name"),
        'leave_trans_count':leave_trans_count,
        'remaining_days': remaining_days
    })
    
def edit_leave_transaction(request,staffno,lt_id):
    staff = get_object_or_404(Employee, pk=staffno) 
    company_info = get_object_or_404(CompanyInformation, staffno=staff)   
    leave_transactions = Staff_Leave.objects.filter(staffno__exact=staffno)
    leave_transaction = get_object_or_404(Staff_Leave, pk=lt_id)
    form = LeaveTransactionForm(request.POST or None, instance=leave_transaction)
    
    if request.method == 'POST':
        form = LeaveTransactionForm(request.POST, instance=leave_transaction)
        if form.is_valid():
            form.save()
            return redirect('leave-transaction', staffno=staffno)
    
    context = {
        'staff': staff,
        'staff_cat': company_info.staff_cat,
        'leave_transactions': leave_transactions,
        'leave_transaction':leave_transaction,
        'form': form,
        'company_info': company_info,
        'LEAVE_TYPE': ChoicesLeaveType.objects.all().values_list("name", "name"),
    }
    
    return render(request, 'hr/leave.html', context)


######################################################################
### Staff education views
######################################################################
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


def delete_prev_work(request,coy_id,staffno):
    company = Prev_Company.objects.get(pk=coy_id)
    # company = company.coy_name
    if request.method == 'POST':
       company.delete()
       return redirect('prev-work', staffno)
    return render(request, 'delete.html',{'obj':company.coy_name})

######################################################################
### End of Staff Previous Work
######################################################################

######################################################################
### Staff Dependants
######################################################################
# def dependants(request,staffno):
#     submitted = False
#     dependant_list = Kith.objects.order_by('kith_dob')
#     staff = Employee.objects.get(pk=staffno)
#     dependants = Kith.objects.order_by('kith_dob').filter(staffno__exact=staffno)
#     if request.method == 'POST':
#         form = KithForm(request.POST)
#         if form.is_valid(): 
#             form.save()
#             return redirect('dependants', staffno)
#         else:
#             print(form.errors)
#     else:
#         form = KithForm
#         if 'submitted' in request.GET:
#             submitted = True
#     context = {'form':form,'dependants':dependants,'staff':staff,'dependant_list':dependant_list,'submitted':submitted,'GENDER':ChoicesGender.objects.all().values_list("name","name"),'DEPENDANTS':ChoicesDependants.objects.all().values_list("name","name")}
#     return render(request,'hr/dependants.html',context)

# def edit_dependants(request,dep_id,staffno):
#     dependant_list = Kith.objects.order_by('kith_dob')
#     staff = Employee.objects.get(pk=staffno)
#     dependants = Kith.objects.order_by('kith_dob').filter(staffno__exact=staffno)
#     coy_count = dependants.count()
#     dependant = Kith.objects.get(pk=dep_id)
#     pkno = dependant.id
#     form = KithForm(request.POST or None,instance=dependant)

#     if request.method == 'POST':
#         form = KithForm(request.POST, instance=dependant)
#         if form.is_valid():
#             form.save()
#             return redirect('dependants', staffno)

#     context = {'pkno':pkno,'form':form,'dependants':dependants,'coy_count':coy_count,'dependant':dependant,'staff':staff,'dependant_list':dependant_list,'GENDER':GENDER,'DEPENDANTS':DEPENDANTS}
#     return render(request, 'hr/dependants.html', context)


# def delete_dependants(request,dep_id,staffno):
#     dependant = Kith.objects.get(pk=dep_id)
#     # dependant = dependant.coy_name
#     if request.method == 'POST':
#        dependant.delete()
#        return redirect('dependants', staffno)
#     return render(request, 'delete.html',{'obj':dependant})

######################################################################
### End of Staff Dependants
######################################################################

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