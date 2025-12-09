from decimal import Decimal, InvalidOperation
import json
from math import e
import pprint
import uuid
from django.http import HttpResponseRedirect, JsonResponse, FileResponse, HttpResponse
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
from collections import defaultdict, OrderedDict
from django.db import connection # type: ignore
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, get_user_model
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
from .service import generate_and_send_otp, send_welcome_email, verify_otp
from django.db.models.functions import Concat, TruncMonth
from django.db.models import F, Value, CharField, Sum, Max, Count
from datetime import date
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from hr.utils.export import render_to_excel, render_to_pdf
from bss.firebase import upload_file_to_firebase, delete_file_from_firebase
import tempfile
import pandas as pd
from ledger.models import Account, Journal, JournalLine, Currency
from django.core.exceptions import ValidationError
from calendar import month_name, monthrange





logger = logging.getLogger('activity')


def _clear_pending_otp_state(request):
    for key in ('pending_otp_user_id', 'pending_otp_backend', 'pending_otp_email'):
        if key in request.session:
            request.session.pop(key, None)

def parse_date(date_str):
    if not date_str:
        return None 
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected format is YYYY-MM-DD.")


def to_bool(val):
    return str(val).strip().lower() in ['true', '1', 'yes']


def safe_decimal(value, default=Decimal('0.00')):
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    cleaned = str(value).strip()
    if not cleaned:
        return default
    cleaned = cleaned.replace(',', '')
    try:
        return Decimal(cleaned)
    except (InvalidOperation, TypeError):
        return default


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
            # print("Someone is creating an account", form.cleaned_data)
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            if User.objects.filter(email=email).exists():
                messages.error(request, "Oops, Email address already exists. Please use another email.")
                return redirect('admin-create-account')
            new_user = form.save()
            try:
                send_welcome_email(new_user)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to send welcome email to %s: %s", new_user.username, exc, exc_info=True)
            messages.success(request, f"Account Creation for {username} has been successful")  
            logger.info(f"Account Creation for {username} has been successful")
            return redirect('login')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{error}")
            print(form.errors)
            return redirect('admin-create-account')
    
    context = {'form': form}
    print(context)
    return render(request, 'authentication/register.html', context)

def waiting_approval(request):
    return render(request, 'authentication/waiting_approval.html')


# Login Route
def index(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user_model = get_user_model()
        try:
            user_lookup = user_model.objects.get(email=email)
        except user_model.DoesNotExist:
            messages.error(request, "Email not found.")
            return redirect('login')

        user = authenticate(request, username=user_lookup.username, password=password)
        logger.debug("Login attempt for %s returned %s", email, "success" if user else "failure")

        if user is None:
            messages.error(request, "Invalid login credentials.")
            return redirect('login')

        if not user.approval and not user.is_superuser:
            logger.warning("Login attempt by unapproved user: %s", user.username)
            messages.error(request, "Your account requires administrator approval before you can log in. Please contact the system administrator for assistance.")                    
            return redirect('waiting-approval')

        try:
            generate_and_send_otp(user)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to send OTP for user %s: %s", user.username, exc, exc_info=True)
            messages.error(request, "We could not send your verification code. Please contact the system administrator.")
            return redirect('login')

        auth_backend = getattr(user, 'backend', 'django.contrib.auth.backends.ModelBackend')
        request.session['pending_otp_user_id'] = user.id
        request.session['pending_otp_backend'] = auth_backend
        request.session['pending_otp_email'] = user.email

        messages.info(request, "A verification code has been sent to your email address.")
        return redirect('otp-verify')

    return render(request, 'authentication/login.html', {})


def otp_verify(request):
    user_id = request.session.get('pending_otp_user_id')
    if not user_id:
        messages.error(request, "Your session has expired. Please sign in again.")
        return redirect('login')

    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        _clear_pending_otp_state(request)
        messages.error(request, "We could not find your account information. Please sign in again.")
        return redirect('login')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'resend':
            try:
                generate_and_send_otp(user)
                messages.info(request, "A new verification code has been sent to your email.")
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to resend OTP for user %s: %s", user.username, exc, exc_info=True)
                messages.error(request, "We could not resend the verification code. Please contact the system administrator.")
            return redirect('otp-verify')

        otp_code = (request.POST.get('otp') or '').strip()
        if not otp_code:
            messages.error(request, "Please enter the verification code.")
        else:
            is_valid, feedback = verify_otp(user, otp_code)
            if is_valid:
                auth_backend = request.session.get('pending_otp_backend', 'django.contrib.auth.backends.ModelBackend')
                login(request, user, backend=auth_backend)
                logger.info("OTP verified successfully for user %s", user.username)
                messages.success(request, f"Login successful. Welcome back {user.username}.")
                _clear_pending_otp_state(request)
                return redirect('landing')
            messages.error(request, feedback)

    context = {
        'email': request.session.get('pending_otp_email'),
    }
    return render(request, 'authentication/otp_verify.html', context)


def password_reset_request(request):
    """
    Step 1: User enters email to request password reset.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, "Please enter your email address.")
            return redirect('password-reset-request')
        
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email=email)
        except user_model.DoesNotExist:
            # Don't reveal if email exists for security
            messages.info(request, "If an account exists with that email, a password reset code has been sent.")
            return redirect('password-reset-request')
        
        if not user.email:
            messages.error(request, "This account does not have an email address. Please contact the administrator.")
            return redirect('password-reset-request')
        
        try:
            from .service import generate_and_send_password_reset_otp
            generate_and_send_password_reset_otp(user)
            request.session['password_reset_user_id'] = user.id
            request.session['password_reset_email'] = user.email
            messages.success(request, "A password reset code has been sent to your email address.")
            logger.info(f"Password reset OTP requested for user {user.username} ({user.email})")
            return redirect('password-reset-verify')
        except Exception as exc:
            logger.error("Failed to send password reset OTP for user %s: %s", user.username, exc, exc_info=True)
            messages.error(request, "We could not send the password reset code. Please contact the system administrator.")
            return redirect('password-reset-request')
    
    return render(request, 'authentication/password_reset_request.html')


def password_reset_verify(request):
    """
    Step 2: User enters OTP code to verify identity.
    """
    user_id = request.session.get('password_reset_user_id')
    if not user_id:
        messages.error(request, "Your session has expired. Please request a new password reset.")
        return redirect('password-reset-request')
    
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        _clear_password_reset_state(request)
        messages.error(request, "We could not find your account information. Please request a new password reset.")
        return redirect('password-reset-request')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'resend':
            try:
                from .service import generate_and_send_password_reset_otp
                generate_and_send_password_reset_otp(user)
                messages.info(request, "A new password reset code has been sent to your email.")
            except Exception as exc:
                logger.error("Failed to resend password reset OTP for user %s: %s", user.username, exc, exc_info=True)
                messages.error(request, "We could not resend the password reset code. Please contact the system administrator.")
            return redirect('password-reset-verify')
        
        otp_code = (request.POST.get('otp') or '').strip()
        if not otp_code:
            messages.error(request, "Please enter the verification code.")
        else:
            from .service import verify_otp
            is_valid, feedback = verify_otp(user, otp_code)
            if is_valid:
                request.session['password_reset_verified'] = True
                messages.success(request, "Verification successful. Please set your new password.")
                logger.info(f"Password reset OTP verified for user {user.username}")
                return redirect('password-reset-confirm')
            messages.error(request, feedback)
    
    context = {
        'email': request.session.get('password_reset_email'),
    }
    return render(request, 'authentication/password_reset_verify.html', context)


def password_reset_confirm(request):
    """
    Step 3: User sets new password after OTP verification.
    """
    user_id = request.session.get('password_reset_user_id')
    verified = request.session.get('password_reset_verified', False)
    
    if not user_id or not verified:
        messages.error(request, "Your session has expired or verification is required. Please start over.")
        _clear_password_reset_state(request)
        return redirect('password-reset-request')
    
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        _clear_password_reset_state(request)
        messages.error(request, "We could not find your account information. Please request a new password reset.")
        return redirect('password-reset-request')
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        if not new_password or not confirm_password:
            messages.error(request, "Please fill in all fields.")
        elif new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        else:
            try:
                from django.contrib.auth.password_validation import validate_password
                validate_password(new_password, user)
                user.set_password(new_password)
                user.save()
                logger.info(f"Password reset completed successfully for user {user.username}")
                messages.success(request, "Your password has been reset successfully. You can now log in with your new password.")
                _clear_password_reset_state(request)
                return redirect('login')
            except Exception as e:
                error_messages = []
                if hasattr(e, 'messages'):
                    error_messages = e.messages
                else:
                    error_messages = [str(e)]
                for msg in error_messages:
                    messages.error(request, msg)
    
    return render(request, 'authentication/password_reset_confirm.html')


def _clear_password_reset_state(request):
    """Clear password reset session variables."""
    for key in ('password_reset_user_id', 'password_reset_email', 'password_reset_verified'):
        if key in request.session:
            request.session.pop(key, None)


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
    _clear_pending_otp_state(request)
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

    # Get gender data from Employee model
    gender_data = (Employee.objects.values('gender').exclude(companyinformation__active_status='Inactive').annotate(count=Count('staffno')))

    gender_labels = [g['gender'] for g in gender_data]
    gender_counts = [g['count'] for g in gender_data]
    
    staff_per_staff_category = (CompanyInformation.objects.values('staff_cat').exclude(active_status='Inactive').annotate(count=Count('staffno', distinct=True)).order_by('staff_cat'))
    line_labels = [s['staff_cat'] for s in staff_per_staff_category]
    line_counts = [s['count'] for s in staff_per_staff_category]

    
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
        
        'gender_labels': json.dumps(gender_labels),
        'gender_counts': json.dumps(gender_counts),
        'line_labels': json.dumps(line_labels),
        'line_counts': json.dumps(line_counts),
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
    filter_campus = None
    filter_rank = None

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
        filter_campus = request.POST.getlist('filter_campus')
        filter_rank = request.POST.getlist('filter_rank')

        # Filter by Staff Category
        if filter_staffcategory:
            filters &= Q(companyinformation__staff_cat__in=filter_staffcategory)

        # Filter by Contract Type
        if filter_contract:
            filters &= Q(companyinformation__contract__in=filter_contract)
            
        # Filter by Campus
        if filter_campus:
            filters &= Q(companyinformation__campus__in=filter_campus)

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
            
        if filter_rank:
            company_info = CompanyInformation.objects.filter(rank__in=filter_rank)
            company_staffno = {company.staffno_id for company in company_info}
            filters &= Q(staffno__in=company_staffno)
        
            
        print("Filters being applied", filter_campus)
                      
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
        'jobtitle': [(q.staff_rank, q.staff_rank) for q in StaffRank.objects.all()],
        'rank': [(q.job_title, q.job_title) for q in JobTitle.objects.all()],
        'directorate': [(q.direct_name, q.direct_name) for q in Directorate.objects.all()],
        'school_faculty': [(q.sch_fac_name, q.sch_fac_name) for q in School_Faculty.objects.all()],
        'campus': [(q.campus_name, q.campus_name) for q in Campus.objects.all()],
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
        'filter_campus': filter_campus,
        'filter_age': filter_age,
        'filter_rank': filter_rank,
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
    
    
    
# Staff Dashboard Views
def staff_dashboard(request):
    return render(request, 'hr/staff_dashboard.html', {})

    
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
            messages.error(request, form.errors)
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
        messages.error(request, form.errors)
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
# Write a function for bulk upload csv format fro staff information and income uplaod
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


@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('staff_income_upload')
def staff_income_upload(request):
    """
    Dynamic CSV upload for Income and Deduction data.
    Flow: Select Upload Type (Income/Deduction) → Select Specific Type → Upload CSV
    """
    print(f"[STAFF_INCOME_UPLOAD] Request method: {request.method}, User: {request.user.username}")
    upload_type = request.POST.get('upload_type') or request.GET.get('upload_type', '')
    selected_type = request.POST.get('selected_type') or request.GET.get('selected_type', '')
    print(f"[STAFF_INCOME_UPLOAD] Upload type: {upload_type}, Selected type: {selected_type}")
    
    # Get available types
    income_types = IncomeType.objects.all().order_by('name')
    deduction_types = DeductionType.objects.all().order_by('name')
    
    # Handle CSV upload
    if request.method == 'POST' and 'csv_file' in request.FILES:
        csv_file = request.FILES['csv_file']
        upload_type = request.POST.get('upload_type')
        selected_type = request.POST.get('selected_type')
        
        if not upload_type or not selected_type:
            print(f"[STAFF_INCOME_UPLOAD] ERROR: Missing upload_type or selected_type")
            messages.error(request, 'Please select both upload type and specific type before uploading.')
            context = {
                'upload_type': upload_type,
                'selected_type': selected_type,
                'income_types': income_types,
                'deduction_types': deduction_types,
            }
            return render(request, 'hr/staff_income_upload.html', context)
        
        if not csv_file.name.endswith('.csv'):
            print(f"[STAFF_INCOME_UPLOAD] ERROR: Invalid file type - {csv_file.name}")
            messages.error(request, 'This is not a CSV file.')
            context = {
                'upload_type': upload_type,
                'selected_type': selected_type,
                'income_types': income_types,
                'deduction_types': deduction_types,
            }
            return render(request, 'hr/staff_income_upload.html', context)
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            reader = csv.DictReader(decoded_file.splitlines())
            
            # Expected CSV columns (case-insensitive)
            required_columns = ['staffno', 'amount']
            optional_columns = ['activate_now', 'one_time_payment']
            
            # Normalize column names (case-insensitive)
            if not reader.fieldnames:
                print(f"[STAFF_INCOME_UPLOAD] ERROR: CSV file has no headers")
                messages.error(request, 'CSV file appears to be empty or has no headers.')
                context = {
                    'upload_type': upload_type,
                    'selected_type': selected_type,
                    'income_types': income_types,
                    'deduction_types': deduction_types,
                }
                return render(request, 'hr/staff_income_upload.html', context)
            
            header_map = {col.strip().lower(): col.strip() for col in reader.fieldnames}
            
            # Check required columns
            missing_columns = []
            for req_col in required_columns:
                if req_col.lower() not in header_map:
                    missing_columns.append(req_col)
            
            if missing_columns:
                print(f"[STAFF_INCOME_UPLOAD] ERROR: Missing required columns: {missing_columns}")
                messages.error(request, f'Missing required columns in CSV: {", ".join(missing_columns)}')
                context = {
                    'upload_type': upload_type,
                    'selected_type': selected_type,
                    'income_types': income_types,
                    'deduction_types': deduction_types,
                }
                return render(request, 'hr/staff_income_upload.html', context)
            
            errors = []
            success_count = 0
            total_rows = 0
            
            print(f"[STAFF_INCOME_UPLOAD] Starting to process CSV rows...")
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
                    total_rows += 1
                    try:
                        # Get values using case-insensitive lookup
                        staffno = row.get(header_map.get('staffno', ''), '').strip()
                        amount_str = row.get(header_map.get('amount', ''), '').strip()
                        activate_now_str = row.get(header_map.get('activate_now', 'true'), '').strip().lower()
                        one_time_str = row.get(header_map.get('one_time_payment', 'false'), '').strip().lower()
                        print(f"[STAFF_INCOME_UPLOAD] Processing row {row_num}: staffno={staffno}, amount={amount_str}, activate_now={activate_now_str}, one_time={one_time_str}")
                        
                        if not staffno:
                            errors.append(f"Row {row_num}: Staff number is required")
                            continue
                        
                        if not amount_str:
                            errors.append(f"Row {row_num}: Amount is required")
                            continue
                        
                        try:
                            amount = Decimal(amount_str.replace(',', ''))
                            print(f"[STAFF_INCOME_UPLOAD] Row {row_num}: Amount parsed successfully: {amount}")
                        except (InvalidOperation, ValueError):
                            errors.append(f"Row {row_num}: Invalid amount format: {amount_str}")
                            continue
                        
                        # Parse boolean values
                        is_active = activate_now_str in ('true', '1', 'yes', 'y', 'on') if activate_now_str else True
                        is_one_time = one_time_str in ('true', '1', 'yes', 'y', 'on') if one_time_str else False
                        
                        # Get employee
                        try:
                            employee = Employee.objects.get(staffno=staffno)
                        except Employee.DoesNotExist:
                            errors.append(f"Row {row_num}: Employee with staff number '{staffno}' not found")
                            continue
                        
                        # Process based on upload type
                        if upload_type == 'income':
                            if selected_type.lower() == 'basic salary':
                                # Update CompanyInformation salary
                                print(f"[STAFF_INCOME_UPLOAD] Row {row_num}: Processing Basic Salary update for {staffno}")
                                try:
                                    company_info = CompanyInformation.objects.get(staffno=employee)
                                    old_salary = company_info.salary
                                    company_info.salary = str(amount)
                                    company_info.save(update_fields=['salary'])
                                    success_count += 1
                                    print(f"[STAFF_INCOME_UPLOAD] Row {row_num}: SUCCESS - Updated basic salary from {old_salary} to {amount} for {employee.fname} {employee.lname}")
                                    logger.info(f"Updated basic salary from {old_salary} to {amount} for {employee.fname} {employee.lname} ({staffno}) by {request.user.username}")
                                except CompanyInformation.DoesNotExist:
                                    errors.append(f"Row {row_num}: Company information not found for staff {staffno}")
                                except Exception as e:
                                    errors.append(f"Row {row_num}: Error updating basic salary: {str(e)}")
                            else:
                                # Create/update StaffIncome
                                print(f"[STAFF_INCOME_UPLOAD] Row {row_num}: Processing Income '{selected_type}' for {staffno}")
                                staff_income, created = StaffIncome.objects.update_or_create(
                                    staffno=employee,
                                    income_type=selected_type,
                                    defaults={
                                        'amount': amount,
                                        'is_active': is_active,
                                        'is_one_time': is_one_time,
                                        'income_entitlement': Decimal('100.00'),
                                    }
                                )
                                success_count += 1
                                action = 'created' if created else 'updated'
                                print(f"[STAFF_INCOME_UPLOAD] Row {row_num}: SUCCESS - {action.capitalize()} income '{selected_type}' for {employee.fname} {employee.lname}: {amount}")
                                logger.info(f"{action.capitalize()} income '{selected_type}' for {employee.fname} {employee.lname} ({staffno}): {amount} by {request.user.username}")
                        
                        elif upload_type == 'deduction':
                            # Create/update StaffDeduction
                            print(f"[STAFF_INCOME_UPLOAD] Row {row_num}: Processing Deduction '{selected_type}' for {staffno}")
                            staff_deduction, created = StaffDeduction.objects.update_or_create(
                                staffno=employee,
                                deduction_type=selected_type,
                                defaults={
                                    'amount': amount,
                                    'is_active': is_active,
                                    'is_one_time': is_one_time,
                                }
                            )
                            success_count += 1
                            action = 'created' if created else 'updated'
                            print(f"[STAFF_INCOME_UPLOAD] Row {row_num}: SUCCESS - {action.capitalize()} deduction '{selected_type}' for {employee.fname} {employee.lname}: {amount}")
                            logger.info(f"{action.capitalize()} deduction '{selected_type}' for {employee.fname} {employee.lname} ({staffno}): {amount} by {request.user.username}")
                    
                    except Exception as e:
                        errors.append(f"Row {row_num}: Unexpected error: {str(e)}")
                        logger.error(f"Error processing row {row_num} in CSV upload: {e}", exc_info=True)
            
            # Report results
            if success_count > 0:
                messages.success(request, f'Successfully processed {success_count} record(s).')
            if errors:
                error_message = f"Errors occurred during upload:\n" + "\n".join(errors[:20])  # Show first 20 errors
                if len(errors) > 20:
                    error_message += f"\n... and {len(errors) - 20} more errors."
                messages.error(request, error_message)
            
            # Redirect with state preserved if there were errors, otherwise clear state
            if errors:
                url = reverse('staff-income-upload')
                return redirect(url)
        
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            context = {
                'upload_type': upload_type,
                'selected_type': selected_type,
                'income_types': income_types,
                'deduction_types': deduction_types,
            }
            return render(request, 'hr/staff_income_upload.html', context)
    
    # GET request or initial load
    context = {
        'upload_type': upload_type,
        'selected_type': selected_type,
        'income_types': income_types,
        'deduction_types': deduction_types,
    }
    return render(request, 'hr/staff_income_upload.html', context)
        



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
            # surcharge = ent.get_surcharge(staff)
            surcharge_details = ent.get_surcharge_details(staff)
            
            
            treatment_summary.append({
                'type': ttype,
                'entitlement': ent.entitlement,
                'used': used,
                'remaining': remaining,
                'gross_surcharge': surcharge_details['gross_surcharge'],
                'surcharge_paid': surcharge_details['total_paid'],
                'surcharge_balance': surcharge_details['balance'],
                'monthly_deduction': surcharge_details['monthly_deduction'],
            })
            
    # Get active surcharges for this staff
    active_surcharges = MedicalSurcharge.objects.filter(staffno=staff, status__in=['pending', 'active'])

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
            
            # Check if this transaction creates a surcharge
            check_and_create_surcharge(medical_transaction)

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
        'active_surcharges': active_surcharges,
    }
    return render(request, 'hr/medical.html', context)



def check_and_create_surcharge(medical_transaction):
    """Automatically create surcharge record if transaction exceeds entitlement"""
    staff = medical_transaction.staffno
    company_info = CompanyInformation.objects.get(staffno=staff)
    
    # Get entitlement for this treatment type
    entitlement = MedicalEntitlement.objects.filter(
        staff_cat=company_info.staff_cat,
        treatment_type=medical_transaction.nature,
        academic_year=medical_transaction.academic_year
    ).first()
    
    if entitlement:
        total_used = Medical.objects.filter(
            staffno=staff,
            nature=medical_transaction.nature,
            academic_year=medical_transaction.academic_year
        ).aggregate(models.Sum('treatment_cost'))['treatment_cost__sum'] or 0
        
        if total_used > entitlement.entitlement:
            # Calculate the surcharge amount for this specific transaction
            previous_used = total_used - medical_transaction.treatment_cost
            
            if previous_used < entitlement.entitlement:
                # This transaction caused the surcharge
                surcharge_amount = total_used - entitlement.entitlement
            else:
                # Already in surcharge, this entire transaction is surcharge
                surcharge_amount = medical_transaction.treatment_cost
            
            # Create surcharge record if it doesn't exist
            if surcharge_amount > 0:
                MedicalSurcharge.objects.create(
                    staffno=staff,
                    medical_transaction=medical_transaction,
                    total_amount=surcharge_amount,
                    balance=surcharge_amount,
                    academic_year=medical_transaction.academic_year,
                    status='pending'
                )



@login_required
@role_required(['superadmin', 'hr officer', 'hr admin'])
def manage_medical_surcharge(request, staffno, surcharge_id):
    """Manage surcharge installments and payment plans"""
    surcharge = get_object_or_404(MedicalSurcharge, pk=surcharge_id, staffno=staffno)
    
    if request.method == 'POST':
        installments = int(request.POST.get('installments', 1))
        is_active = request.POST.get('is_active')
        monthly_deduction = request.POST.get('monthly_deduction')
        
        if isinstance(monthly_deduction, str):
            monthly_deduction = monthly_deduction.replace("₵", "").strip()

        monthly_deduction = Decimal(monthly_deduction)
        
        if installments > 0 and is_active:
            surcharge.installments = installments
            surcharge.monthly_deduction = monthly_deduction
            surcharge.is_active = is_active
            surcharge.status = 'active'
            surcharge.save()
            
            messages.success(request, f'Surcharge payment plan created: {installments} installments of ₵{monthly_deduction}')
            return redirect('medical-transaction', staffno=surcharge.staffno.staffno)
    
    context = {
        'surcharge': surcharge,
        'staff': surcharge.staffno,
        'payments': surcharge.payments.all().order_by('payment_date')
    }
    return render(request, 'hr/manage_surcharge.html', context)




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
@tag_required('modify_staff_relief')
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
@tag_required('approve_payroll')
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
        
        for staff in staff_list:
            company_info = CompanyInformation.objects.filter(staffno=staff).first()
            if not company_info:
                continue
                
            try:
                with transaction.atomic():
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
                            'ssf_employee': payroll.get_ssnit_contribution()["amount"],
                            'ssf_employer': payroll.get_employer_ssnit_contribution()["amount"],
                            'pf_employee': payroll.get_pf_contribution()["amount"], 
                            'pf_employer': payroll.get_employer_pf_contribution()["amount"],
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
                        payroll_obj.ssf_employee = payroll.get_ssnit_contribution()["amount"]
                        payroll_obj.ssf_employer = payroll.get_employer_ssnit_contribution()["amount"]    
                        payroll_obj.pf_employee = payroll.get_pf_contribution()["amount"]
                        payroll_obj.pf_employer = payroll.get_employer_pf_contribution()["amount"]
                        payroll_obj.total_deduction = payroll.get_total_deductions()
                        payroll_obj.net_salary = payroll.get_net_salary()
                        payroll_obj.cost_center = company_info.cost_center
                        payroll_obj.paye_total_income = payroll.get_miscellaneous_and_benefit_in_kind()
                        payroll_obj.paye_total_emoluments = payroll.get_entitled_basic_salary() + payroll.get_miscellaneous_and_benefit_in_kind()
                        payroll_obj.total_relief = payroll.get_staff_relief()["total_relief"]
                        payroll_obj.net_taxable_pay = payroll.get_taxable_income()
                        payroll_obj.save()
                    
                    # Track which income/deduction types we've processed
                    processed_incomes = set()
                    processed_deductions = set()
                    processed_reliefs = set()
                    processed_benefits = set()
                    
                    print("About to push income deduction into their model")
                    
                    # Save/Update Basic Salary as income
                    income_obj, _ = PayrollIncome.objects.update_or_create(
                        payroll=payroll_obj,
                        income_type='Basic Salary',
                        defaults={'amount': payroll.get_entitled_basic_salary()}
                    )
                    processed_incomes.add('Basic Salary')
                    
                    # Save/Update Allowances/Incomes
                    allowances = payroll.get_allowance_values()
                    for income in allowances['incomes']:
                        if income['entitled_amount'] > 0:
                            income_obj, _ = PayrollIncome.objects.update_or_create(
                                payroll=payroll_obj,
                                income_type=income['income_type'],
                                defaults={
                                    'amount': income['entitled_amount'],
                                    'percentage_of_basic': income.get('percentage_on_basic')
                                }
                            )
                            processed_incomes.add(income['income_type'])
                    
                    # Delete incomes that are no longer applicable
                    payroll_obj.incomes.exclude(income_type__in=processed_incomes).delete()
                    
                    # Save Deductions
                    # 1. Income Tax
                    income_tax = payroll.get_income_tax()
                    if income_tax['tax'] > 0:
                        ded_obj, _ = PayrollDeduction.objects.update_or_create(
                            payroll=payroll_obj,
                            deduction_type='Income Tax',
                            defaults={'amount': income_tax['tax']}
                        )
                        processed_deductions.add('Income Tax')
                    
                    # 2. SSF Employee
                    ssf_employee = payroll.get_ssnit_contribution()
                    if ssf_employee['amount'] > 0:
                        deduction_type = f'Social Security ({ssf_employee["rate"]}%)'
                        ded_obj, _ = PayrollDeduction.objects.update_or_create(
                            payroll=payroll_obj,
                            deduction_type=deduction_type,
                            defaults={
                                'amount': ssf_employee['amount'],
                                'rate': ssf_employee['rate']
                            }
                        )
                        processed_deductions.add(deduction_type)
                        
                    
                    # 3. PF Employee
                    pf_employee = payroll.get_pf_contribution()
                    if pf_employee['amount'] > 0:
                        deduction_type = f'Provident Fund ({pf_employee["rate"]}%)'
                        ded_obj, _ = PayrollDeduction.objects.update_or_create(
                            payroll=payroll_obj,
                            deduction_type=deduction_type,
                            defaults={
                                'amount': pf_employee['amount'],
                                'rate': pf_employee['rate']
                            }
                        )
                        processed_deductions.add(deduction_type)
                    
                    # 4. Withholding Tax (Rent and others)
                    tax_details = payroll.get_tax_for_taxable_income()
                    
                    # Rent Tax
                    if tax_details['rent_tax'] > 0:
                        ded_obj, _ = PayrollDeduction.objects.update_or_create(
                            payroll=payroll_obj,
                            deduction_type='WHT - Rent',
                            defaults={
                                'amount': tax_details['rent_tax']
                                # 'rate': tax_details['rent_tax_detail']['tax_rate'] if tax_details['rent_tax_detail'] else None
                            }
                        )
                        processed_deductions.add('WHT - Rent')
                    
                    #  Withholding Taxes
                    if tax_details['total_tax'] > 0:
                        ded_obj, _ = PayrollDeduction.objects.update_or_create(
                            payroll=payroll_obj,
                            deduction_type='Withholding Tax',
                            defaults={
                                'amount': tax_details['total_tax']
                                # 'rate': tax_details['tax_breakdown']['tax_rate'] if tax_details['tax_breakdown'] else None
                            }
                        )
                        processed_deductions.add('Withholding Tax')
                    
                    # 5. Other Deductions (including loans)
                    deductions = payroll.get_deductions()
                    for deduction in deductions['deductions']:
                        if deduction['deductable_amount'] > 0:
                            ded_obj, _ = PayrollDeduction.objects.update_or_create(
                                payroll=payroll_obj,
                                deduction_type=deduction['deduction_type'],
                                defaults={'amount': deduction['deductable_amount']}
                            )
                            processed_deductions.add(deduction['deduction_type'])
                    
                    # Delete deductions that are no longer applicable
                    payroll_obj.deductions.exclude(deduction_type__in=processed_deductions).delete()
                    
                    # Save Reliefs
                    # Save/Update Reliefs
                    reliefs = payroll.get_staff_relief()
                    for relief in reliefs['relief_list']:
                        if relief['amount'] > 0:
                            rel_obj, _ = PayrollRelief.objects.update_or_create(
                                payroll=payroll_obj,
                                relief_type=relief['relief_type'],
                                defaults={'amount': relief['amount']}
                            )
                            processed_reliefs.add(relief['relief_type'])
                    
                    # Delete reliefs that are no longer applicable
                    payroll_obj.reliefs.exclude(relief_type__in=processed_reliefs).delete()
                    
                    # Save/Update Benefits in Kind
                    bik = payroll.get_benefits_in_kind()['benefit_in_kind']
                    if bik['rent_bik'] > 0:
                        ben_obj, _ = PayrollBenefitInKind.objects.update_or_create(
                            payroll=payroll_obj,
                            benefit_type='Rent Benefit',
                            defaults={'amount': bik['rent_bik']}
                        )
                        processed_benefits.add('Rent Benefit')
                        
                    if bik['fuel_bik'] > 0:
                        ben_obj, _ = PayrollBenefitInKind.objects.update_or_create(
                            payroll=payroll_obj,
                            benefit_type='Fuel Benefit',
                            defaults={'amount': bik['fuel_bik']}
                        )
                        processed_benefits.add('Fuel Benefit')
                        
                    if bik['vechile_bik'] > 0:
                        ben_obj, _ = PayrollBenefitInKind.objects.update_or_create(
                            payroll=payroll_obj,
                            benefit_type='Vehicle Benefit',
                            defaults={'amount': bik['vechile_bik']}
                        )
                        processed_benefits.add('Vehicle Benefit')
                        
                    if bik['driver_bik'] > 0:
                        ben_obj, _ = PayrollBenefitInKind.objects.update_or_create(
                            payroll=payroll_obj,
                            benefit_type='Driver Benefit',
                            defaults={'amount': bik['driver_bik']}
                        )
                        processed_benefits.add('Driver Benefit')
                    
                    # Delete benefits that are no longer applicable
                    payroll_obj.benefits_in_kind.exclude(benefit_type__in=processed_benefits).delete()
                    # Handle Loan Payments
                    loan_deductions = payroll.get_active_loan_deductions()
                    for loan in loan_deductions:
                        monthly_payment = loan["monthly_installment"]
                        loan_obj = StaffLoan.objects.filter(id=loan["id"]).first()
                        
                        if loan_obj:
                            loan_payment, created = LoanPayment.objects.get_or_create(
                                loan=loan_obj,
                                payment_date=current_month_date,
                                defaults={'amount_paid': monthly_payment}
                            )
                            
                            if created:
                                loan_obj.months_left -= 1
                                if loan_obj.months_left <= 0:
                                    loan_obj.is_active = False
                                loan_obj.save()
                            else:
                                loan_payment.amount_paid = monthly_payment
                                loan_payment.save()
                    
                    # Handle Medical Surcharge Payments
                    surcharge_deductions = payroll.get_active_surcharge_deductions()
                    for surcharge in surcharge_deductions:
                        surcharge_obj = MedicalSurcharge.objects.filter(id=surcharge["surcharge_id"]).first()
                        
                        if surcharge_obj:
                            # Create payment record
                            surcharge_payment, created = MedicalSurchargePayment.objects.get_or_create(
                                surcharge=surcharge_obj,
                                payment_date=current_month_date,
                                defaults={'amount': surcharge["amount"]}
                            )
                            
                            if not created:
                                # Update existing payment if needed
                                surcharge_payment.amount = surcharge["amount"]
                                surcharge_payment.save()
                        
            except (TypeError, InvalidOperation) as e:
                skipped_staff.append(f"{staff.fname} {staff.lname} ({staff.staffno})")
                logger.error(f"Error processing payroll for {staff.staffno}: {str(e)}")
                continue
        
        if skipped_staff:
            messages.error(request, f"The following staff were skipped due to errors: {', '.join(skipped_staff)}")

        messages.success(request, f"Payroll for {current_month_date.strftime('%B %Y')} has been processed. You can update once not approved")   
        logger.info(f"Payroll for {current_month_date.strftime('%B %Y')} has been processed")     
        return redirect('payroll-post-payroll')
    
    payrolls_group = (
        Payroll.objects.values('month').annotate(
            latest_id=Max('id'), 
            staff_count=Count('staffno')
        ).order_by('-month'))

    payrolls = []
    for item in payrolls_group:
        payroll = Payroll.objects.get(id=item['latest_id'])
        payroll.staff_count = item['staff_count']
        payrolls.append(payroll)
        
    context = {"selected_month": selected_month, "payrolls": payrolls}
    return render(request, 'payroll/finalise_payroll.html', context)


@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('process_single_payroll')
def payroll_details(request, staffno):
    staff = Employee.objects.get(pk=staffno)
    company_info = CompanyInformation.objects.get(staffno=staff)
    selected_month = request.GET.get("filter_by_month")
    selected_year = request.GET.get("filter_by_year")
    payroll_data = {}
    

    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)
        # current_month_date = date.fromisoformat(selected_month)
        payroll = PayrollCalculator(staffno=staff, month=selected_date)
        

        loan_details = payroll.get_active_loan_deductions()
        # Calculate loan totals for payslip
        loan_totals = {
            "principal_amount": Decimal('0.00'),
            "opening_balance": Decimal('0.00'),
            "monthly_installment": Decimal('0.00'),
            "outstanding_balance": Decimal('0.00'),
        }
        for loan in loan_details:
            loan_totals["principal_amount"] += Decimal(str(loan["meta"]["principal_amount"]))
            loan_totals["opening_balance"] += Decimal(str(loan["meta"]["opening_balance"]))
            loan_totals["monthly_installment"] += Decimal(str(loan["monthly_installment"]))
            loan_totals["outstanding_balance"] += Decimal(str(loan["meta"]["outstanding_balance"]))
        
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
            "employer_ssf": payroll.get_employer_ssnit_contribution()["amount"],
            "employer_pf": payroll.get_employer_pf_contribution()["amount"],
            "withholding_tax": payroll.get_tax_for_taxable_income()["total_tax"],
            "withholding_rent_tax": payroll.get_tax_for_taxable_income()["rent_tax"],
            "benefits_in_kind": payroll.get_benefits_in_kind()["benefit_in_kind"],
            "loan_details": loan_details,
            "loan_totals": loan_totals,
        }
        messages.success(request, f"Payslip for {staff.fname} has been generated")        

    
    # Export functionality
    export_format = request.GET.get("format")
    if export_format and payroll_data:
        filename = f"Payslip {staff.fname} {staff.lname} {selected_date.strftime('%B %Y')}"
        
        if export_format == "pdf":
            context = {
                'staff': staff,
                'company_info': company_info,
                'payroll_data': payroll_data,
                "selected_month": selected_month,
                "selected_year": selected_year,
            }
            
        return render_to_pdf('export/payslip.html', context, f"{filename}.pdf")
    
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
                    "employer_ssf": payroll.get_employer_ssnit_contribution()["amount"],
                    "employer_pf": payroll.get_employer_pf_contribution()["amount"],
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

    # Export functionality
    export_format = request.GET.get("format")
    if export_format and all_payrolls and selected_month and selected_year:
        filename = f"Payroll_Processing_{selected_date.strftime('%b_%Y')}"
        
        if export_format == "pdf":
            context = {
                "payrolls": all_payrolls,
                "selected_date": selected_date.strftime('%B %Y'),
                "date": datetime.now().strftime("%d %B, %Y"),
                "total_staff": len(all_payrolls),
            }
            return render_to_pdf("export/payslip_document.html", context, f"{filename}.pdf")
            
    context = {
        "payrolls": all_payrolls,
        "selected_month": selected_month,
        "selected_year": selected_year,
    }

    return render(request, "hr/payroll_processing.html", context)
def payslip_test(request):
    return render(request, "export/payslip_document.html")

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
    
    selected_month = request.GET.get("filter_by_month")
    selected_year = request.GET.get("filter_by_year")
    selected_staff_cat = request.GET.get("staff_cat", None)
    selected_campus = request.GET.get("campus", None)
    selected_school = request.GET.get("school", None) 
    selected_department = request.GET.get("department", None)
    selected_directorate = request.GET.get("directorate", None)
    selected_bank = request.GET.get("bank", None)    
        
    all_payrolls = []
    grouped_payrolls = defaultdict(list)
    subtotals = defaultdict(lambda: {
        'basic_salary': Decimal('0.00'),
        'total_income': Decimal('0.00'),
        'gross_salary': Decimal('0.00'),
        'income_tax': Decimal('0.00'),
        'deductions': Decimal('0.00'),
        'ssf_employee': Decimal('0.00'),
        'pf_employee': Decimal('0.00'),
        'employer_pf': Decimal('0.00'),
        'total_deduction': Decimal('0.00'),
        'net_salary': Decimal('0.00'),
    })
    
    grand_total = {
        'basic_salary': Decimal('0.00'),
        'total_income': Decimal('0.00'),
        'gross_salary': Decimal('0.00'),
        'income_tax': Decimal('0.00'),
        'deductions': Decimal('0.00'),
        'ssf_employee': Decimal('0.00'),
        'pf_employee': Decimal('0.00'),
        'employer_pf': Decimal('0.00'),
        'total_deduction': Decimal('0.00'),
        'net_salary': Decimal('0.00'),
    }
    
    group_by_field = None
    current_month_date = None
    
    if selected_month and selected_year:
        current_month_date = date(int(selected_year), int(selected_month), 28)
        
        # Check if payroll exists for this month
        if not Payroll.objects.filter(month=current_month_date).exists():
            messages.error(request, f"Payroll for {current_month_date.strftime('%B %Y')} has not been processed.")
            return redirect('payroll-register')
        
        # Build the query for Payroll records
        payroll_query = Payroll.objects.filter(month=current_month_date)
        
        # Handle "all" option for grouping and filtering
        if selected_staff_cat == "all":
            group_by_field = 'staff_cat'
        elif selected_staff_cat and selected_staff_cat != "all":
            payroll_query = payroll_query.filter(staffno__companyinformation__staff_cat=selected_staff_cat)
            
        if selected_school == "all":
            group_by_field = 'school'
        elif selected_school and selected_school != "all":
            payroll_query = payroll_query.filter(staffno__companyinformation__sch_fac_dir=selected_school)
            
        if selected_department == "all":
            group_by_field = 'department'
        elif selected_department and selected_department != "all":
            payroll_query = payroll_query.filter(staffno__companyinformation__dept=selected_department)
            
        if selected_directorate == "all":
            group_by_field = 'directorate'
        elif selected_directorate and selected_directorate != "all":
            payroll_query = payroll_query.filter(staffno__companyinformation__directorate=selected_directorate)
            
        if selected_bank == "all":
            group_by_field = 'bank'
        elif selected_bank and selected_bank != "all":
            payroll_query = payroll_query.filter(staffno__companyinformation__bank_name=selected_bank)
            
        if selected_campus == "all":
            group_by_field = 'campus'
        elif selected_campus and selected_campus != "all":
            payroll_query = payroll_query.filter(staffno__companyinformation__campus=selected_campus)
        
        # Exclude inactive staff
        payroll_query = payroll_query.exclude(
            staffno__companyinformation__active_status='Inactive'
        )
        
        # Prefetch related data for efficiency
        payroll_query = payroll_query.select_related(
            'staffno'
        ).prefetch_related(
            'staffno'
        ).order_by('staffno__fname', 'staffno__lname')
        
        if not payroll_query.exists():
            messages.error(request, "No payroll records found for the selected criteria.")
            return redirect('payroll-register')

        for payroll_record in payroll_query:
            staff = payroll_record.staffno
            company_info = CompanyInformation.objects.get(staffno=staff)
            
            if not company_info:
                continue
            
            # Use saved payroll data
            payroll_data = {
                "staff": staff,
                "company_info": company_info,
                "month": current_month_date.strftime("%B %Y"),
                "basic_salary": payroll_record.basic_salary or Decimal('0.00'),
                "total_income": payroll_record.total_income or Decimal('0.00'),
                "gross_salary": payroll_record.gross_salary or Decimal('0.00'),
                "income_tax": payroll_record.income_tax or Decimal('0.00'),
                "deductions": payroll_record.other_deductions or Decimal('0.00'),
                "ssf_employee": payroll_record.ssf_employee or Decimal('0.00'),
                "pf_employee": payroll_record.pf_employee or Decimal('0.00'),
                "employer_pf": payroll_record.pf_employer or Decimal('0.00'),
                "total_deduction": payroll_record.total_deduction or Decimal('0.00'),
                "net_salary": payroll_record.net_salary or Decimal('0.00'),
            }
            
            # Determine group key
            group_key = None
            if group_by_field:
                if group_by_field == 'staff_cat':
                    group_key = company_info.staff_cat
                elif group_by_field == 'school':
                    group_key = company_info.sch_fac_dir
                elif group_by_field == 'department':
                    group_key = company_info.dept
                elif group_by_field == 'directorate':
                    group_key = company_info.directorate
                elif group_by_field == 'bank':
                    group_key = company_info.bank_name
                elif group_by_field == 'campus':
                    group_key = company_info.campus
                    
            if group_key:
                grouped_payrolls[group_key].append(payroll_data)
                # Update subtotals
                subtotals[group_key]['basic_salary'] += payroll_data['basic_salary']
                subtotals[group_key]['total_income'] += payroll_data['total_income']
                subtotals[group_key]['gross_salary'] += payroll_data['gross_salary']
                subtotals[group_key]['income_tax'] += payroll_data['income_tax']
                subtotals[group_key]['deductions'] += payroll_data['deductions']
                subtotals[group_key]['ssf_employee'] += payroll_data['ssf_employee']
                subtotals[group_key]['pf_employee'] += payroll_data['pf_employee']
                subtotals[group_key]['employer_pf'] += payroll_data['employer_pf']
                subtotals[group_key]['total_deduction'] += payroll_data['total_deduction']
                subtotals[group_key]['net_salary'] += payroll_data['net_salary']
            else:
                all_payrolls.append(payroll_data)
            
            # Update grand totals
            grand_total['basic_salary'] += payroll_data['basic_salary']
            grand_total['total_income'] += payroll_data['total_income']
            grand_total['gross_salary'] += payroll_data['gross_salary']
            grand_total['income_tax'] += payroll_data['income_tax']
            grand_total['deductions'] += payroll_data['deductions']
            grand_total['ssf_employee'] += payroll_data['ssf_employee']
            grand_total['pf_employee'] += payroll_data['pf_employee']
            grand_total['employer_pf'] += payroll_data['employer_pf']
            grand_total['total_deduction'] += payroll_data['total_deduction']
            grand_total['net_salary'] += payroll_data['net_salary']
            
        messages.success(request, f"Payroll Register for {current_month_date.strftime('%B %Y')} has been loaded successfully")
    # Export functionality
    export_format = request.GET.get("format")
    if export_format and (all_payrolls or grouped_payrolls) and current_month_date:
        filename = f"Payroll Register {current_month_date.strftime('%b_%Y')}"
        
        if export_format == "pdf":
            context = {
                "payrolls": all_payrolls,
                "grouped_payrolls": dict(grouped_payrolls),
                "subtotals": dict(subtotals),
                "grand_total": grand_total,
                "selected_date": current_month_date.strftime('%B %Y'),
                "date": datetime.now().strftime("%d %B, %Y"),
                "group_by_field": group_by_field,
            }
            return render_to_pdf("export/payroll_register.html", context, f"{filename}.pdf")
            
        elif export_format == "excel":
            rows = []
            
            if grouped_payrolls:
                for group_key, group_data in grouped_payrolls.items():
                    # Add group header
                    rows.append({
                        "Employee ID": f"--- {group_key} ---",
                        "Employee Name": "",
                        "Basic Salary": "",
                        "Allowances": "",
                        "Gross Salary": "",
                        "Income Tax": "",
                        "Deductions": "",
                        "SSF Employee": "",
                        "PF Employee": "",
                        "PF Employer": "",
                        "Total Deduction": "",
                        "Net Pay": "",
                    })
                    
                    # Add group data
                    for entry in group_data:
                        rows.append({
                            "Employee ID": entry["staff"].staffno,
                            "Employee Name": f"{entry['staff'].fname} {entry['staff'].lname}",
                            "Basic Salary": float(entry["basic_salary"]),
                            "Allowances": float(entry["total_income"]),
                            "Gross Salary": float(entry["gross_salary"]),
                            "Income Tax": float(entry["income_tax"]),
                            "Deductions": float(entry["deductions"]),
                            "SSF Employee": float(entry["ssf_employee"]),
                            "PF Employee": float(entry["pf_employee"]),
                            "PF Employer": float(entry["employer_pf"]),
                            "Total Deduction": float(entry["total_deduction"]),
                            "Net Pay": float(entry["net_salary"]),
                        })
                    
                    # Add subtotal
                    rows.append({
                        "Employee ID": "",
                        "Employee Name": f"Subtotal - {group_key}",
                        "Basic Salary": float(subtotals[group_key]['basic_salary']),
                        "Allowances": float(subtotals[group_key]['total_income']),
                        "Gross Salary": float(subtotals[group_key]['gross_salary']),
                        "Income Tax": float(subtotals[group_key]['income_tax']),
                        "Deductions": float(subtotals[group_key]['deductions']),
                        "SSF Employee": float(subtotals[group_key]['ssf_employee']),
                        "PF Employee": float(subtotals[group_key]['pf_employee']),
                        "PF Employer": float(subtotals[group_key]['employer_pf']),
                        "Total Deduction": float(subtotals[group_key]['total_deduction']),
                        "Net Pay": float(subtotals[group_key]['net_salary']),
                    })
                    rows.append({})  # Empty row for spacing
            else:
                for entry in all_payrolls:
                    rows.append({
                        "Employee ID": entry["staff"].staffno,
                        "Employee Name": f"{entry['staff'].fname} {entry['staff'].lname}",
                        "Basic Salary": float(entry["basic_salary"]),
                        "Allowances": float(entry["total_income"]),
                        "Gross Salary": float(entry["gross_salary"]),
                        "Income Tax": float(entry["income_tax"]),
                        "Deductions": float(entry["deductions"]),
                        "SSF Employee": float(entry["ssf_employee"]),
                        "PF Employee": float(entry["pf_employee"]),
                        "PF Employer": float(entry["employer_pf"]),
                        "Total Deduction": float(entry["total_deduction"]),
                        "Net Pay": float(entry["net_salary"]),
                    })
            
            # Add grand total
            rows.append({
                "Employee ID": "",
                "Employee Name": "GRAND TOTAL",
                "Basic Salary": float(grand_total['basic_salary']),
                "Allowances": float(grand_total['total_income']),
                "Gross Salary": float(grand_total['gross_salary']),
                "Income Tax": float(grand_total['income_tax']),
                "Deductions": float(grand_total['deductions']),
                "SSF Employee": float(grand_total['ssf_employee']),
                "PF Employee": float(grand_total['pf_employee']),
                "PF Employer": float(grand_total['employer_pf']),
                "Total Deduction": float(grand_total['total_deduction']),
                "Net Pay": float(grand_total['net_salary']),
            })
            
            return render_to_excel({"Payroll Register": rows}, f"{filename}.xlsx")
    
    context = {
        "payrolls": all_payrolls,
        "grouped_payrolls": dict(grouped_payrolls),
        "subtotals": dict(subtotals),
        "grand_total": grand_total,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "staff_categories": staff_categories,
        "campus": campus,
        "schools": schools,
        "departments": departments,
        "banks": banks,
        "directorate": directorate,
        "selected_staff_cat": selected_staff_cat,
        "selected_campus": selected_campus, 
        "selected_school": selected_school,
        "selected_department": selected_department,
        "selected_bank": selected_bank,
        "selected_directorate": selected_directorate,
        "group_by_field": group_by_field,
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
@role_required(['superadmin', 'finance admin'])
@tag_required('apply_salary_increment')
def staff_salary_increment(request):
    staff_categories = StaffCategory.objects.all()
    staff_list = []
    increment_percentage = None
    increment_amount = None
    selected_staff_cat = None

    # allowance_types = (
    #     StaffIncome.objects.filter(is_active=True)
    #     .exclude(income_type__isnull=True)
    #     .exclude(income_type__exact='')
    #     .values_list('income_type', flat=True)
    #     .distinct()
    #     .order_by('income_type')
    # )
    
    allowance_types = IncomeType.objects.all().order_by('name')
    
    selected_allowance = None
    allowance_staff_list = []
    allowance_increment_percentage = None
    selected_allowance_staff_ids = []

    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'salary')

        if form_type == 'salary':
            selected_staff_cat = request.POST.get('staff_cat')
            increment_percentage = request.POST.get('increment_percentage')
            increment_amount = request.POST.get('increment_amount')
            selected_staff = request.POST.getlist('selected_staff')

            if selected_staff_cat:
                company_infos = (
                    CompanyInformation.objects.filter(staff_cat=selected_staff_cat)
                    .exclude(active_status__in=['Inactive', 'Dormant'])
                    .select_related('staffno')
                )
                staff_list = [info.staffno for info in company_infos]

            if request.POST.get('apply_salary_increment') == '1':
                if not selected_staff:
                    messages.error(request, "Please select staff before applying an increment.")
                elif increment_percentage and increment_amount:
                    messages.error(request, "Enter either a percentage or an amount, not both.")
                elif not increment_percentage and not increment_amount:
                    messages.error(request, "Please enter a percentage or an amount to apply.")
                else:
                    salary_increment_decimal = None
                    salary_increment_amount = None
                    use_percentage = bool(increment_percentage)

                    if use_percentage:
                        try:
                            salary_increment_decimal = Decimal(increment_percentage)
                        except InvalidOperation:
                            messages.error(request, "Please enter a valid increment percentage for salary.")
                    else:
                        try:
                            salary_increment_amount = Decimal(increment_amount)
                        except InvalidOperation:
                            messages.error(request, "Please enter a valid increment amount for salary.")

                    if (use_percentage and salary_increment_decimal is not None) or (
                        not use_percentage and salary_increment_amount is not None
                    ):
                        for staff_id in selected_staff:
                            staff = get_object_or_404(Employee, pk=staff_id)
                            company_info = get_object_or_404(CompanyInformation, staffno=staff)
                            current_salary = safe_decimal(company_info.salary)

                            if use_percentage:
                                increment_delta = current_salary * (salary_increment_decimal / Decimal('100'))
                                action_summary = f"{salary_increment_decimal}%"
                            else:
                                increment_delta = salary_increment_amount
                                action_summary = f"{salary_increment_amount}"

                            new_salary = (current_salary + increment_delta).quantize(Decimal('0.01'))

                            company_info.salary = new_salary
                            company_info.save(update_fields=['salary'])

                        messages.success(
                            request,
                            f"Salary increment ({action_summary}) applied to {len(selected_staff)} staff."
                        )
                        logger.info(
                            "Salary increment (%s) applied to staff %s by %s.",
                            action_summary,
                            selected_staff,
                            request.user.username,
                        )
                        return redirect('payroll-salary-increment')

        elif form_type == 'allowance':
            selected_allowance = request.POST.get('allowance_type')
            allowance_increment_percentage = request.POST.get('allowance_percentage')
            selected_allowance_staff_ids = request.POST.getlist('selected_allowance_staff')

            if selected_allowance:
                allowance_staff_queryset = (
                    StaffIncome.objects.filter(
                        income_type__iexact=selected_allowance,
                        is_active=True
                    )
                    .exclude(staffno__companyinformation__active_status__in=['Inactive', 'Dormant'])
                    .select_related('staffno')
                    .order_by('staffno__lname', 'staffno__fname')
                )
                allowance_staff_list = list(allowance_staff_queryset)

            if request.POST.get('apply_allowance_increment') == '1':
                if not selected_allowance:
                    messages.error(request, "Please choose an allowance before applying an increment.")
                elif not allowance_increment_percentage:
                    messages.error(request, "Please enter an increment percentage for the allowance.")
                elif not selected_allowance_staff_ids:
                    messages.error(request, "Please select at least one staff member for the allowance increment.")
                elif not allowance_staff_list:
                    messages.warning(
                        request,
                        f"No active staff allowances found for {selected_allowance}."
                    )
                else:
                    try:
                        allowance_increment_decimal = Decimal(allowance_increment_percentage)
                    except InvalidOperation:
                        messages.error(request, "Please enter a valid increment percentage for the allowance.")
                    else:
                        incomes_to_update = [
                            income for income in allowance_staff_list
                            if str(income.id) in selected_allowance_staff_ids
                        ]

                        if not incomes_to_update:
                            messages.error(request, "Selected staff could not be matched. Please try again.")
                            return redirect('payroll-salary-increment')

                        updated_records = 0
                        for income in incomes_to_update:
                            current_amount = safe_decimal(income.amount)
                            increment_amount = current_amount * (allowance_increment_decimal / Decimal('100'))
                            new_amount = (current_amount + increment_amount).quantize(Decimal('0.01'))

                            income.amount = new_amount
                            income.save(update_fields=['amount'])
                            updated_records += 1

                        messages.success(
                            request,
                            f"{allowance_increment_decimal}% increment applied to {updated_records} staff for {selected_allowance}."
                        )
                        logger.info(
                            "%s%% allowance increment applied to %s for allowance %s by %s.",
                            allowance_increment_decimal,
                            updated_records,
                            selected_allowance,
                            request.user.username,
                        )
                        return redirect('payroll-salary-increment')

    context = {
        'staff_categories': staff_categories,
        'staff_list': staff_list,
        'increment_percentage': increment_percentage,
        'increment_amount': increment_amount,
        'selected_staff_cat': selected_staff_cat,
        'allowance_types': allowance_types,
        'selected_allowance': selected_allowance,
        'allowance_staff_list': allowance_staff_list,
        'allowance_increment_percentage': allowance_increment_percentage,
        'selected_allowance_staff_ids': selected_allowance_staff_ids,
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
    totals = {
        'basic_salary': Decimal('0.00'),
        'total_income': Decimal('0.00'),
        'gross_salary': Decimal('0.00'),
        'income_tax': Decimal('0.00'),
        'ssf_employee': Decimal('0.00'),
        'pf_employee': Decimal('0.00'),
        'pf_employer': Decimal('0.00'),
        'other_deductions': Decimal('0.00'),
        'total_deduction': Decimal('0.00'),
        'net_salary': Decimal('0.00'),
    }
    
    if selected_month and selected_year:
        current_month_date = date(int(selected_year), int(selected_month), 28)
        
        if not Payroll.objects.filter(month=current_month_date).exists():
            messages.error(request, f"Payroll for {current_month_date.strftime('%B %Y')} has not been processed.")
            return redirect('payroll-history')
        
        if staffno and staffno != "all":
            staff = get_object_or_404(Employee, pk=staffno)
            staff_list = [staff]
        elif staffno == "all":
            staff_list = Employee.objects.all()
        else:
            staff_list = []

        for staff in staff_list:
            if not Payroll.objects.filter(staffno=staff, month__year=current_month_date.year, month__month=current_month_date.month).exists():
                continue
            
            # payrolls = Payroll.objects.filter(staffno=staff, month=current_month_date)
            payroll = Payroll.objects.filter(staffno=staff, month__year=current_month_date.year, month__month=current_month_date.month).first()
            if payroll:
                entry = {
                    "staff": staff,
                    "basic_salary": payroll.basic_salary or Decimal('0.00'),
                    "total_income": payroll.total_income or Decimal('0.00'),
                    "gross_salary": payroll.gross_salary or Decimal('0.00'),
                    "income_tax": payroll.income_tax or Decimal('0.00'),
                    "ssf_employee": payroll.ssf_employee or Decimal('0.00'),
                    "pf_employee": payroll.pf_employee or Decimal('0.00'),
                    "pf_employer": payroll.pf_employer or Decimal('0.00'),
                    "other_deductions": payroll.other_deductions or Decimal('0.00'),
                    "total_deduction": payroll.total_deduction or Decimal('0.00'),
                    "net_salary": payroll.net_salary or Decimal('0.00'),
                    "for_month": current_month_date,
                }
                payroll_data.append(entry)
                
                # Calculate totals
                totals['basic_salary'] += entry['basic_salary'] 
                totals['total_income'] += entry['total_income']
                totals['gross_salary'] += entry['gross_salary']
                totals['income_tax'] += entry['income_tax']
                totals['ssf_employee'] += entry['ssf_employee']
                totals['pf_employee'] += entry['pf_employee']
                totals['pf_employer'] += entry['pf_employer']
                totals['other_deductions'] += entry['other_deductions']
                totals['total_deduction'] += entry['total_deduction']
                totals['net_salary'] += entry['net_salary']
                

    export_format = request.GET.get("format")
    if export_format and payroll_data:
        filename = f"PAYROLL_HISTORY__{current_month_date.strftime('%b_%Y')}"
        if export_format == "pdf":
            context = {
                "payroll_data": payroll_data,
                "totals": totals,
                "selected_date": current_month_date.strftime('%B %Y'),
                "date": datetime.now().strftime("%d %B, %Y")
            }
            return render_to_pdf("export/payroll_history.html", context, f"{filename}.pdf")
        elif export_format == "excel":
            rows = []
            for entry in payroll_data:
                staff = entry["staff"]
                
                rows.append({
                    "Employee ID": staff.staffno,
                    "Employee Name": f"{staff.lname} {staff.fname} {staff.middlenames}",
                    "Basic Salary": entry["basic_salary"],
                    "Total Income": entry["total_income"],
                    "Gross Salary": entry["gross_salary"],
                    "Income Tax": entry["income_tax"],
                    "SSF Employee": entry["ssf_employee"],
                    "PF Employee": entry["pf_employee"],
                    "PF Employer": entry["pf_employer"],
                    "Other Deductions": entry["other_deductions"],
                    "Total Deduction": entry["total_deduction"],
                    "Net Salary": entry["net_salary"],
                })
                
            rows.append({
                "Employee ID": "",
                "Employee Name": "TOTAL",
                "Basic Salary": totals['basic_salary'],
                "Total Income": totals['total_income'],
                "Gross Salary": totals['gross_salary'],
                "Income Tax": totals['income_tax'],
                "SSF Employee": totals['ssf_employee'],
                "PF Employee": totals['pf_employee'],
                "PF Employer": totals['pf_employer'],
                "Other Deductions": totals['other_deductions'],
                "Total Deduction": totals['total_deduction'],
                "Net Salary": totals['net_salary'],
            })

            return render_to_excel({"PAYROLL History": rows}, f"{filename}.xlsx")


    return render(request, "hr/payroll_history.html", {
        "payroll_data": payroll_data,
        "totals": totals,
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
    total_amount = Decimal('0.00')
    
    statutory_types = ["Basic Salary"]

    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)

        # ✅ only allow if payroll for selected month is approved
        if not Payroll.objects.filter(month=selected_date).exists():
            messages.error(request, f"Payroll for {selected_date.strftime('%B %Y')} has not been proccessed")
            return redirect('income-history')
        
        # Build the query - DO NOT use .first() here!
        payroll_query = Payroll.objects.filter(month=selected_date)
        
        # Filter by staff
        if staffno and staffno != "all":
            payroll_query = payroll_query.filter(staffno__pk=staffno)
        elif staffno == "all":
            payroll_query = payroll_query.all()
        else:
            messages.error(request, "Please select a staff member or 'All Staff'")
            return redirect('income-history')
            
        # Prefetch related income data
        payroll_query = payroll_query.prefetch_related(
            'incomes',
            'staffno'
        ).order_by('staffno__lname', 'staffno__fname')
        
        # Iterate through ALL payroll records in the queryset
        for payroll_record in payroll_query:
            staff = payroll_record.staffno
            
            # Get incomes from PayrollIncome table
            income_records = payroll_record.incomes.all()
            
            # Filter by income type if specified
            if income_type_id and income_type_id != "all":
                income_records = income_records.filter(income_type=income_type_id)
            
            for income in income_records:
                income_data.append({
                    "staff": staff,
                    "income_type": income.income_type,
                    "amount": income.amount,
                    "percentage_of_basic": income.percentage_of_basic,
                    "for_month": selected_date,
                })
                total_amount += income.amount
                
        # Export PDF/Excel
        export_format = request.GET.get("format")
        if export_format and income_data:
            itype_for_filename = (income_type_id or "All")
            filename = f"{itype_for_filename} {selected_date.strftime('%b_%Y')}"
            if export_format == "pdf":
                context = {
                    "income_data": income_data,
                    "total_amount": total_amount,
                    "selected_date": selected_date.strftime('%B %Y'),
                    "date": datetime.now().strftime("%d %B, %Y")
                }
                return render_to_pdf("export/incomes.html", context, f"{filename}.pdf")

            if export_format == "excel":
                rows = []
                for entry in income_data:
                    rows.append({
                        "Employee ID": entry["staff"].staffno,
                        "Employee": f"{entry['staff'].fname} {entry['staff'].lname} {entry['staff'].middlenames}",
                        "Income Type": entry["income_type"],
                        "Amount": entry["amount"],
                    })
                    
                rows.append({})  # Empty row
                rows.append({
                    "Employee ID": "",
                    "Employee": "TOTAL",
                    "Income Type": "",
                    "Amount": float(total_amount),
                })
                return render_to_excel({"Income History": rows}, f"{filename}.xlsx")
                       
    context = {
        "income_data": income_data,
        "employees": Employee.objects.all().order_by('lname'),
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
    total_amount = Decimal('0.00')
    
    statutory_types = ["Income Tax", "WHT - Rent", "Withholding Tax"]


    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)

        # Check if payroll exists
        if not Payroll.objects.filter(month=selected_date).exists():
            messages.error(request, f"Payroll for {selected_date.strftime('%B %Y')} has not been processed.")
            return redirect('deduction-history')

        # Build the query
        payroll_query = Payroll.objects.filter(month=selected_date)
        
        # Filter by staff
        if staffno and staffno != "all":
            payroll_query = payroll_query.filter(staffno__pk=staffno)
        elif staffno == "all":
            payroll_query = payroll_query.all()
        else:
            messages.error(request, "Please select a staff member or 'All Staff'")
            return redirect('deduction-history')
            
        # Prefetch related deduction data
        payroll_query = payroll_query.prefetch_related(
            'deductions',
            'staffno'
        ).order_by('staffno__lname', 'staffno__fname')
        
        # Iterate through ALL payroll records in the queryset
        for payroll_record in payroll_query:
            staff = payroll_record.staffno
            
            # Get deductions from PayrollDeduction table
            # EXCLUDE SSF and PF deductions
            deduction_records = payroll_record.deductions.exclude(
                deduction_type__startswith="Social Security"
            ).exclude(
                deduction_type__startswith="Provident Fund"
            )
            
            # Filter by deduction type if specified
            if deduction_type_id and deduction_type_id != "all":
                deduction_records = deduction_records.filter(deduction_type=deduction_type_id)
            
            for deduction in deduction_records:
                # Format rate if it exists
                rate_str = None
                if deduction.rate:
                    rate_str = f"{deduction.rate}"
                
                deduction_data.append({
                    "staff": staff,
                    "deduction_type": deduction.deduction_type,
                    "amount": deduction.amount,
                    "percentage": rate_str,
                    "for_month": selected_date,
                })
                total_amount += deduction.amount
                
        # Export PDF/Excel
        export_format = request.GET.get("format")
        if export_format and deduction_data:
            dtype_for_filename = (deduction_type_id or "All")
            filename = f"{dtype_for_filename} {selected_date.strftime('%b_%Y')}"
            
            if export_format == "pdf":
                context = {
                    "deduction_data": deduction_data,
                    "total_amount": total_amount,
                    "selected_date": selected_date.strftime('%B %Y'),
                    "date": datetime.now().strftime("%d %B, %Y")
                }
                return render_to_pdf("export/deductions.html", context, f"{filename}.pdf")
                
            elif export_format == "excel":
                rows = []
                for entry in deduction_data:
                    rows.append({
                        "Employee ID": entry["staff"].staffno,
                        "Employee": f"{entry['staff'].fname} {entry['staff'].lname}",
                        "Deduction Type": entry["deduction_type"],
                        "Amount": float(entry["amount"]),
                    })
                    
                rows.append({})  # Empty row
                rows.append({
                    "Employee ID": "",
                    "Employee": "TOTAL",
                    "Deduction Type": "",
                    "Amount": float(total_amount),
                })
                return render_to_excel({"Deduction History": rows}, f"{filename}.xlsx")
    
    
    context = {
        "deduction_data": deduction_data,
        "employees": Employee.objects.all().order_by('lname'),
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
@tag_required('view_statutory_history')
def statutory_history(request):
    selected_month = request.GET.get("filter_by_month")
    selected_year = request.GET.get("filter_by_year")
    staffno = request.GET.get("staffno")
    selected_type = request.GET.get("statutory_type")

    statutory_rows = []
    total_employee = Decimal('0.00')
    total_employer = Decimal('0.00')
    total_overall = Decimal('0.00')

    if selected_month and selected_year and selected_type in ["ssf", "pf"]:
        selected_date = date(int(selected_year), int(selected_month), 28)

        # Check if payroll exists
        if not Payroll.objects.filter(month=selected_date).exists():
            messages.error(request, f"Payroll for {selected_date.strftime('%B %Y')} has not been processed.")
            return redirect('statutory-history')
        
        # Build the query
        payroll_query = Payroll.objects.filter(month=selected_date)
        
        # Filter by contribution type
        if selected_type == "ssf":
            payroll_query = payroll_query.filter(
                staffno__companyinformation__ssn_con=True
            )
        else:  # pf
            payroll_query = payroll_query.filter(
                staffno__companyinformation__pf_con=True
            )
        
        # Filter by staff
        if staffno and staffno != "all":
            payroll_query = payroll_query.filter(staffno__pk=staffno)
            
            # Check if specific staff has the contribution enabled
            if not payroll_query.exists():
                if selected_type == "ssf":
                    messages.error(request, "This staff doesn't pay SSF or no payroll found.")
                else:
                    messages.error(request, "This staff doesn't pay Provident Fund or no payroll found.")
                return redirect('statutory-history')
        elif staffno != "all":
            messages.error(request, "Please select a staff member or 'All Staff'")
            return redirect('statutory-history')
        
        # Prefetch related data for efficiency
        payroll_query = payroll_query.select_related(
            'staffno'
        ).prefetch_related(
            'staffno'
        ).order_by('staffno__lname', 'staffno__fname')

        # Process payroll records
        for payroll_record in payroll_query:
            staff = payroll_record.staffno
            
            employee_amt = Decimal('0.00')
            employer_amt = Decimal('0.00')

            if selected_type == "ssf":
                employee_amt = payroll_record.ssf_employee or Decimal('0.00')
                employer_amt = payroll_record.ssf_employer or Decimal('0.00')
            else:  # pf
                employee_amt = payroll_record.pf_employee or Decimal('0.00')
                employer_amt = payroll_record.pf_employer or Decimal('0.00')

            total_amt = employee_amt + employer_amt

            statutory_rows.append({
                "staff": staff,
                "for_month": selected_date,
                "employee": employee_amt,
                "employer": employer_amt,
                "total": total_amt,
            })

            total_employee += employee_amt
            total_employer += employer_amt
            total_overall += total_amt

        # Export
        export_format = request.GET.get("format")
        if export_format and statutory_rows:
            filename = f"{selected_type.upper()} {selected_date.strftime('%b_%Y')}"
            if export_format == "pdf":
                context = {
                    "rows": statutory_rows,
                    "selected_date": selected_date.strftime('%B %Y'),
                    "type": selected_type,
                    "totals": {
                        "employee": total_employee,
                        "employer": total_employer,
                        "overall": total_overall,
                    },
                    "date": datetime.now().strftime("%d %B, %Y")
                }
                return render_to_pdf("export/statutory.html", context, f"{filename}.pdf")
            elif export_format == "excel":
                rows = []
                for entry in statutory_rows:
                    rows.append({
                        "Staff No": entry["staff"].staffno,
                        "Staff": f"{entry['staff'].fname} {entry['staff'].lname}",
                        ("SSF Employee" if selected_type == "ssf" else "PF Employee"): float(entry["employee"]),
                        ("SSF Employer" if selected_type == "ssf" else "PF Employer"): float(entry["employer"]),
                        "Total": float(entry["total"]),
                    })
                # Totals row
                rows.append({})
                rows.append({
                    "Staff No": "",
                    "Staff": "TOTAL",
                    ("SSF Employee" if selected_type == "ssf" else "PF Employee"): float(total_employee),
                    ("SSF Employer" if selected_type == "ssf" else "PF Employer"): float(total_employer),
                    "Total": float(total_overall),
                })
                sheet_name = "SSF History" if selected_type == "ssf" else "PF History"
                return render_to_excel({sheet_name: rows}, f"{filename}.xlsx")


    context = {
        "rows": statutory_rows,
        "employees": Employee.objects.all().order_by('lname'),
        "selected_month": selected_month,
        "selected_year": selected_year,
        "report_for": staffno,
        "selected_type": selected_type,
        "totals": {
            "employee": total_employee,
            "employer": total_employer,
            "overall": total_overall,
        }
    }

    return render(request, "hr/statutory_history.html", context)


def payslip(request):
    return render(request, "payroll/test.html")

@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('view_paye_history')
def paye_history(request):
    selected_month = request.GET.get("filter_by_month")
    selected_year = request.GET.get("filter_by_year")
    staffno = request.GET.get("staffno")
    
    paye_data = []
    totals = {
        'basic_salary': Decimal('0.00'),
        'paye_total_income': Decimal('0.00'),
        'paye_total_emoluments': Decimal('0.00'),
        'ssf_employee': Decimal('0.00'),
        'pf_employee': Decimal('0.00'),
        'total_relief': Decimal('0.00'),
        'net_taxable_pay': Decimal('0.00'),
        'income_tax': Decimal('0.00'),
    }
    
    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)

        # Check if payroll exists for this month
        if not Payroll.objects.filter(month=selected_date).exists():
            messages.error(request, f"Payroll for {selected_date.strftime('%B %Y')} has not been processed.")
            return redirect('paye-history')

        # Build the query
        payroll_query = Payroll.objects.filter(month=selected_date)
        
        # Filter by staff
        if staffno and staffno != "all":
            payroll_query = payroll_query.filter(staffno__pk=staffno)
        elif staffno == "all":
            payroll_query = payroll_query.exclude(staffno__companyinformation__active_status='Inactive')
        else:
            messages.error(request, "Please select a staff member or 'All Staff'")
            return redirect('paye-history')
        
        # Prefetch related data for efficiency
        payroll_query = payroll_query.select_related('staffno').prefetch_related('staffno').order_by('staffno__lname', 'staffno__fname')

        # Process all payroll records
        for payroll in payroll_query:
            staff = payroll.staffno
            
            entry = {
                "staff": staff,
                "basic_salary": payroll.basic_salary or Decimal('0.00'),
                "paye_total_income": payroll.paye_total_income or Decimal('0.00'),
                "paye_total_emoluments": payroll.paye_total_emoluments or Decimal('0.00'),
                "ssf_employee": payroll.ssf_employee or Decimal('0.00'),
                "pf_employee": payroll.pf_employee or Decimal('0.00'),
                "total_relief": payroll.total_relief or Decimal('0.00'),
                "net_taxable_pay": payroll.net_taxable_pay or Decimal('0.00'),
                "income_tax": payroll.income_tax or Decimal('0.00'),
                "for_month": selected_date,
            }
            paye_data.append(entry)
            
            # Calculate totals
            totals['basic_salary'] += entry['basic_salary']
            totals['paye_total_income'] += entry['paye_total_income']
            totals['paye_total_emoluments'] += entry['paye_total_emoluments']
            totals['ssf_employee'] += entry['ssf_employee']
            totals['pf_employee'] += entry['pf_employee']
            totals['total_relief'] += entry['total_relief']
            totals['net_taxable_pay'] += entry['net_taxable_pay']
            totals['income_tax'] += entry['income_tax']
    
    # Export PDF/Excel
    export_format = request.GET.get("format")
    if export_format and paye_data:
        filename = f"PAYE {selected_date.strftime('%b_%Y')}"
        if export_format == "pdf":
            context = {
                "paye_data": paye_data,
                "totals": totals,
                "selected_date": selected_date.strftime('%B %Y'),
                "date": datetime.now().strftime("%d %B, %Y")
            }
            return render_to_pdf("export/paye.html", context, f"{filename}.pdf")
        elif export_format == "excel":
            rows = []
            for entry in paye_data:
                staff = entry["staff"]
                
                rows.append({
                    "Employee ID": staff.staffno,
                    "Employee Name": f"{staff.lname} {staff.fname} {staff.middlenames}",
                    "Tax ID": f"{staff.gcardno}",
                    "Basic Wage": entry["basic_salary"],
                    "Total Allowances": entry["paye_total_income"],
                    "Total Emoluments": entry["paye_total_emoluments"],
                    "SSF Employee": entry["ssf_employee"],
                    "PF Employee": entry["pf_employee"],
                    "Total Relief": entry["total_relief"],
                    "Net Taxable Pay": entry["net_taxable_pay"],
                    "Income Tax": entry["income_tax"],
                })
            # Add totals row to Excel
            rows.append({
                "Staff No": "",
                "Staff": "TOTAL",
                "Tax ID": "",
                "Basic Wage": totals['basic_salary'],
                "Total Allowances": totals['paye_total_income'],
                "Total Emoluments": totals['paye_total_emoluments'],
                "SSF Employee": totals['ssf_employee'],
                "PF Employee": totals['pf_employee'],
                "Total Relief": totals['total_relief'],
                "Net Taxable Pay": totals['net_taxable_pay'],
                "Income Tax": totals['income_tax'],
            })
            return render_to_excel({"PAYE History": rows}, f"{filename}.xlsx")
    
    context = {
        "paye_data": paye_data,
        "totals": totals,
        "employees": Employee.objects.exclude(companyinformation__active_status='Inactive').order_by('fname'),
        "selected_month": selected_month,
        "selected_year": selected_year,
        "report_for": staffno,
    }
    
    return render(request, "hr/paye_history.html", context)
@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('view_statutory_history')
def payroll_allowances(request):
    selected_month = request.GET.get("filter_by_month")
    selected_year = request.GET.get("filter_by_year")
    staffno = request.GET.get("staffno")
    
    allowances_data = []
    grand_totals = {}
    overall_total = Decimal('0.00')
    
    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)

        # Check if payroll exists
        if not Payroll.objects.filter(month=selected_date).exists():
            messages.error(request, f"Payroll for {selected_date.strftime('%B %Y')} has not been processed.")
            return redirect('payroll-allowances')

        # Build query
        payroll_query = Payroll.objects.filter(month=selected_date)
        
        if staffno and staffno != "all":
            payroll_query = payroll_query.filter(staffno__pk=staffno)
        elif staffno == "all":
            payroll_query = payroll_query.all()
        else:
            messages.error(request, "Please select a staff member or 'All Staff'")
            return redirect('payroll-allowances')
        
        # Prefetch related data for efficiency
        payroll_query = payroll_query.prefetch_related(
            'incomes',
            # 'benefits_in_kind',
            'staffno'
        ).order_by('staffno__lname', 'staffno__fname')

        for payroll_record in payroll_query:
            staff = payroll_record.staffno
            company_info = CompanyInformation.objects.get(staffno=staff)
            position = company_info.job_title if company_info else "N/A"
            
            employee_allowances = []
            employee_total = Decimal('0.00')
            
            # Get all incomes from the saved records
            for income in payroll_record.incomes.all():
                employee_allowances.append({
                    'type': income.income_type,
                    'amount': income.amount
                })
                employee_total += income.amount
                
                # Update grand totals
                grand_totals[income.income_type] = grand_totals.get(
                    income.income_type, Decimal('0.00')
                ) + income.amount
            
            # Add benefits in kind if needed
            # for benefit in payroll_record.benefits_in_kind.all():
            #     employee_allowances.append({
            #         'type': f'{benefit.benefit_type} (BIK)',
            #         'amount': benefit.amount
            #     })
            #     employee_total += benefit.amount
                
            #     # Update grand totals
            #     grand_totals[f'{benefit.benefit_type} (BIK)'] = grand_totals.get(
            #         f'{benefit.benefit_type} (BIK)', Decimal('0.00')
            #     ) + benefit.amount
            
            if employee_allowances:
                allowances_data.append({
                    'staff': staff,
                    'position': position,
                    'allowances': employee_allowances,
                    'total': employee_total,
                    'for_month': selected_date,
                })
                overall_total += employee_total
    
    # Export functionality
    export_format = request.GET.get("format")
    if export_format and allowances_data:
        filename = f"Payroll Allowances_{selected_date.strftime('%b_%Y')}"
        
        if export_format == "pdf":
            context = {
                "allowances_data": allowances_data,
                "grand_totals": grand_totals,
                "overall_total": overall_total,
                "selected_date": selected_date.strftime('%B %Y'),
                "date": datetime.now().strftime("%d %B, %Y"),
                "report_type": "individual" if staffno != "all" else "all"
            }
            return render_to_pdf("export/payroll_allowances.html", context, f"{filename}.pdf")
            
        elif export_format == "excel":
            rows = []
            for entry in allowances_data:
                # Add employee header
                rows.append({
                    "Employee ID": entry['staff'].staffno,
                    "Employee Name": f"{entry['staff'].fname} {entry['staff'].lname}",
                    "Position": entry['position'],
                    "Type of Allowance": "",
                    "Amount": ""
                })
                
                # Add allowances
                for allowance in entry['allowances']:
                    rows.append({
                        "Employee ID": "",
                        "Employee Name": "",
                        "Position": "",
                        "Type of Allowance": allowance['type'],
                        "Amount": float(allowance['amount'])
                    })
                
                # Add employee total
                rows.append({
                    "Employee ID": "",
                    "Employee Name": "",
                    "Position": "",
                    "Type of Allowance": "Total",
                    "Amount": float(entry['total'])
                })
                
                # Add empty row for spacing
                rows.append({})
            
            # Add grand totals section
            # rows.append({
            #     "Employee ID": "GRAND TOTALS",
            #     "Employee Name": "",
            #     "Position": "",
            #     "Type of Allowance": "",
            #     "Amount": ""
            # })
            
            # for allowance_type, total in sorted(grand_totals.items()):
            #     rows.append({
            #         "Employee ID": "",
            #         "Employee Name": "",
            #         "Position": "",
            #         "Type of Allowance": allowance_type,
            #         "Amount": float(total)
            #     })
            
            # rows.append({
            #     "Employee ID": "",
            #     "Employee Name": "",
            #     "Position": "",
            #     "Type of Allowance": "OVERALL TOTAL",
            #     "Amount": float(overall_total)
            # })
            
            return render_to_excel({"Allowances Register": rows}, f"{filename}.xlsx")
    
    context = {
        "allowances_data": allowances_data,
        "grand_totals": grand_totals,
        "overall_total": overall_total,
        "employees": Employee.objects.exclude(companyinformation__active_status='Inactive').order_by('lname'),
        "selected_month": selected_month,
        "selected_year": selected_year,
        "report_for": staffno,
    }
    
    return render(request, "hr/payroll_allowances.html", context)
@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('view_statutory_history')
def payroll_deductions(request):
    selected_month = request.GET.get("filter_by_month")
    selected_year = request.GET.get("filter_by_year")
    staffno = request.GET.get("staffno")
    
    deductions_data = []
    grand_totals = {}
    overall_total = Decimal('0.00')
    
    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)

        # Check if payroll exists
        if not Payroll.objects.filter(month=selected_date).exists():
            messages.error(request, f"Payroll for {selected_date.strftime('%B %Y')} has not been processed.")
            return redirect('payroll-deductions')

        # Build query
        payroll_query = Payroll.objects.filter(month=selected_date)
        
        if staffno and staffno != "all":
            payroll_query = payroll_query.filter(staffno__pk=staffno)
        elif staffno == "all":
            payroll_query = payroll_query.all()
        else:
            messages.error(request, "Please select a staff member or 'All Staff'")
            return redirect('payroll-deductions')
        
        # Prefetch related data for efficiency
        payroll_query = payroll_query.prefetch_related(
            'deductions',
            'staffno'
        ).order_by('staffno__lname', 'staffno__fname')

        for payroll_record in payroll_query:
            staff = payroll_record.staffno
            company_info = CompanyInformation.objects.get(staffno=staff)
            position = company_info.job_title if company_info else "N/A"
            
            employee_deductions = []
            employee_total = Decimal('0.00')
            
            # Get all deductions from the saved records
            for deduction in payroll_record.deductions.all():
                employee_deductions.append({
                    'type': deduction.deduction_type,
                    'amount': deduction.amount
                })
                employee_total += deduction.amount
                
                # Update grand totals
                grand_totals[deduction.deduction_type] = grand_totals.get(
                    deduction.deduction_type, Decimal('0.00')
                ) + deduction.amount
            
            if employee_deductions:
                deductions_data.append({
                    'staff': staff,
                    'position': position,
                    'deductions': employee_deductions,
                    'total': employee_total,
                    'for_month': selected_date,
                })
                overall_total += employee_total
    
    # Export functionality
    export_format = request.GET.get("format")
    if export_format and deductions_data:
        filename = f"Payroll Deductions_{selected_date.strftime('%b_%Y')}"
        
        if export_format == "pdf":
            context = {
                "deductions_data": deductions_data,
                "grand_totals": grand_totals,
                "overall_total": overall_total,
                "selected_date": selected_date.strftime('%B %Y'),
                "date": datetime.now().strftime("%d %B, %Y"),
                "report_type": "individual" if staffno != "all" else "all"
            }
            return render_to_pdf("export/payroll_deductions.html", context, f"{filename}.pdf")
            
        elif export_format == "excel":
            rows = []
            for entry in deductions_data:
                # Add employee header
                rows.append({
                    "Employee ID": entry['staff'].staffno,
                    "Employee Name": f"{entry['staff'].fname} {entry['staff'].lname}",
                    "Position": entry['position'],
                    "Type of Deduction": "",
                    "Amount": ""
                })
                
                # Add deductions
                for deduction in entry['deductions']:
                    rows.append({
                        "Employee ID": "",
                        "Employee Name": "",
                        "Position": "",
                        "Type of Deduction": deduction['type'],
                        "Amount": float(deduction['amount'])
                    })
                
                # Add employee total
                rows.append({
                    "Employee ID": "",
                    "Employee Name": "",
                    "Position": "",
                    "Type of Deduction": "Total",
                    "Amount": float(entry['total'])
                })
                
                # Add empty row for spacing
                rows.append({})
            
            # Add grand totals
            # rows.append({
            #     "Employee ID": "GRAND TOTALS",
            #     "Employee Name": "",
            #     "Position": "",
            #     "Type of Deduction": "",
            #     "Amount": ""
            # })
            
            # for deduction_type, total in sorted(grand_totals.items()):
            #     rows.append({
            #         "Employee ID": "",
            #         "Employee Name": "",
            #         "Position": "",
            #         "Type of Deduction": deduction_type,
            #         "Amount": float(total)
            #     })
            
            # rows.append({
            #     "Employee ID": "",
            #     "Employee Name": "",
            #     "Position": "",
            #     "Type of Deduction": "OVERALL TOTAL",
            #     "Amount": float(overall_total)
            # })
            
            return render_to_excel({"Deductions Register": rows}, f"{filename}.xlsx")
    
    context = {
        "deductions_data": deductions_data,
        "grand_totals": grand_totals,
        "overall_total": overall_total,
        "employees": Employee.objects.exclude(companyinformation__active_status='Inactive').order_by('lname'),
        "selected_month": selected_month,
        "selected_year": selected_year,
        "report_for": staffno,
    }
    
    return render(request, "hr/payroll_deductions.html", context)



@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('payroll_component_variation')
def payroll_variation(request):
    # Get filter parameters
    prev_month = request.GET.get("prev_month")
    prev_year = request.GET.get("prev_year")
    curr_month = request.GET.get("curr_month")
    curr_year = request.GET.get("curr_year")
    staffno = request.GET.get("staffno")
    component_type = request.GET.get("component_type")
    
    variation_data = []
    component_summary = {}
    staff_summary = {
        'total_staff_prev': 0,
        'total_staff_curr': 0,
        'staff_with_changes': 0,
        'new_components': 0,
        'removed_components': 0,
        'total_prev_amount': Decimal('0.00'),
        'total_curr_amount': Decimal('0.00'),
        'total_variation': Decimal('0.00'),
    }
    
    if all([prev_month, prev_year, curr_month, curr_year]):
        prev_date = date(int(prev_year), int(prev_month), 28)
        curr_date = date(int(curr_year), int(curr_month), 28)
        
        # Validate dates
        if prev_date >= curr_date:
            messages.error(request, "Previous month must be earlier than current month.")
            return redirect('payroll-component-variation')
        
        # Check if payrolls exist
        if not Payroll.objects.filter(month=prev_date).exists():
            messages.error(request, f"Payroll for {prev_date.strftime('%B %Y')} has not been processed.")
            return redirect('payroll-component-variation')
            
        if not Payroll.objects.filter(month=curr_date).exists():
            messages.error(request, f"Payroll for {curr_date.strftime('%B %Y')} has not been processed.")
            return redirect('payroll-component-variation')
        
        # Build queries
        prev_query = Payroll.objects.filter(month=prev_date)
        curr_query = Payroll.objects.filter(month=curr_date)
        
        if staffno and staffno != "all":
            prev_query = prev_query.filter(staffno__pk=staffno)
            curr_query = curr_query.filter(staffno__pk=staffno)
        
        # Prefetch related data based on component type
        if component_type == "allowances":
            prev_query = prev_query.prefetch_related('incomes', 'staffno')
            curr_query = curr_query.prefetch_related('incomes', 'staffno')
        else:  # deductions
            prev_query = prev_query.prefetch_related('deductions', 'staffno')
            curr_query = curr_query.prefetch_related('deductions', 'staffno')
        
        # Get all payroll records
        prev_payrolls = {p.staffno.pk: p for p in prev_query}
        curr_payrolls = {p.staffno.pk: p for p in curr_query}
        
        all_staff_ids = set(prev_payrolls.keys()) | set(curr_payrolls.keys())
        
        for staff_id in all_staff_ids:
            prev_payroll = prev_payrolls.get(staff_id)
            curr_payroll = curr_payrolls.get(staff_id)
            
            staff_variation = {
                'staff': None,
                'company_info': None,
                'prev_components': {},
                'curr_components': {},
                'variations': [],
                'total_prev': Decimal('0.00'),
                'total_curr': Decimal('0.00'),
                'total_diff': Decimal('0.00'),
                'has_changes': False,
            }
            
            # Get staff info
            if prev_payroll:
                staff_variation['staff'] = prev_payroll.staffno
                staff_variation['company_info'] = CompanyInformation.objects.filter(staffno=prev_payroll.staffno).first()
            elif curr_payroll:
                staff_variation['staff'] = curr_payroll.staffno
                staff_variation['company_info'] = CompanyInformation.objects.filter(staffno=curr_payroll.staffno).first()
            
            # Get components based on type
            if component_type == "allowances":
                if prev_payroll:
                    for income in prev_payroll.incomes.all():
                        staff_variation['prev_components'][income.income_type] = income.amount
                        staff_variation['total_prev'] += income.amount
                        
                if curr_payroll:
                    for income in curr_payroll.incomes.all():
                        staff_variation['curr_components'][income.income_type] = income.amount
                        staff_variation['total_curr'] += income.amount
            else:  # deductions
                if prev_payroll:
                    for deduction in prev_payroll.deductions.all():
                        staff_variation['prev_components'][deduction.deduction_type] = deduction.amount
                        staff_variation['total_prev'] += deduction.amount
                        
                if curr_payroll:
                    for deduction in curr_payroll.deductions.all():
                        staff_variation['curr_components'][deduction.deduction_type] = deduction.amount
                        staff_variation['total_curr'] += deduction.amount
            
            # Calculate variations
            all_component_types = set(staff_variation['prev_components'].keys()) | set(staff_variation['curr_components'].keys())
            
            for comp_type in all_component_types:
                prev_amount = staff_variation['prev_components'].get(comp_type, Decimal('0.00'))
                curr_amount = staff_variation['curr_components'].get(comp_type, Decimal('0.00'))
                diff = curr_amount - prev_amount
                
                if prev_amount > 0 and curr_amount > 0:
                    status = 'modified' if diff != 0 else 'unchanged'
                elif prev_amount > 0 and curr_amount == 0:
                    status = 'removed'
                    staff_summary['removed_components'] += 1
                elif prev_amount == 0 and curr_amount > 0:
                    status = 'new'
                    staff_summary['new_components'] += 1
                else:
                    continue
                
                
                
                percentage = calculate_percentage_change(prev_amount, curr_amount)
                
                variation = {
                    'type': comp_type,
                    'prev_amount': prev_amount,
                    'curr_amount': curr_amount,
                    'difference': diff,
                    'percentage': percentage,
                    'status': status
                }
                
                staff_variation['variations'].append(variation)
                
                # Update component summary
                if comp_type not in component_summary:
                    component_summary[comp_type] = {
                        'total_prev': Decimal('0.00'),
                        'total_curr': Decimal('0.00'),
                        'total_diff': Decimal('0.00'),
                        'staff_count': 0,
                        'variations': []
                    }
                
                component_summary[comp_type]['total_prev'] += prev_amount
                component_summary[comp_type]['total_curr'] += curr_amount
                component_summary[comp_type]['total_diff'] += diff
                if diff != 0:
                    component_summary[comp_type]['staff_count'] += 1
                
                if diff != 0:
                    staff_variation['has_changes'] = True
            
            # Calculate total difference
            staff_variation['total_diff'] = staff_variation['total_curr'] - staff_variation['total_prev']
            staff_variation['total_percentage'] = calculate_percentage_change(
                staff_variation['total_prev'], 
                staff_variation['total_curr']
            )
            
            # Sort variations by absolute difference
            staff_variation['variations'].sort(key=lambda x: abs(x['difference']), reverse=True)
            
            # Update staff summary
            if prev_payroll:
                staff_summary['total_staff_prev'] += 1
            if curr_payroll:
                staff_summary['total_staff_curr'] += 1
            if staff_variation['has_changes']:
                staff_summary['staff_with_changes'] += 1
            
            staff_summary['total_prev_amount'] += staff_variation['total_prev']
            staff_summary['total_curr_amount'] += staff_variation['total_curr']
            staff_summary['total_variation'] += staff_variation['total_diff']
            
            # Only add to variation_data if there are changes or if viewing all
            if staff_variation['has_changes'] or request.GET.get('show_all'):
                variation_data.append(staff_variation)
        
        # Sort variation data by total difference
        variation_data.sort(key=lambda x: abs(x['total_diff']), reverse=True)
        
        # Calculate percentages for component summary
        for comp_type, data in component_summary.items():
            data['percentage'] = calculate_percentage_change(data['total_prev'], data['total_curr'])
    
    # Export functionality
    export_format = request.GET.get("format")
    if export_format and variation_data:
        filename = f"Payroll_{component_type.title()}_Variation_{prev_date.strftime('%b%Y')}_vs_{curr_date.strftime('%b%Y')}"
        
        if export_format == "pdf":
            context = {
                "variation_data": variation_data,
                "component_summary": component_summary,
                "staff_summary": staff_summary,
                "prev_date": prev_date.strftime('%B %Y'),
                "curr_date": curr_date.strftime('%B %Y'),
                "component_type": component_type,
                "generated_date": datetime.now().strftime("%d %B, %Y"),
                "show_all": request.GET.get('show_all'),
            }
            return render_to_pdf("export/payroll_component_variation.html", context, f"{filename}.pdf")
            
        elif export_format == "excel":
            return export_component_variation_to_excel(
                variation_data, component_summary, staff_summary, 
                prev_date, curr_date, component_type, filename
            )
    
    context = {
        "variation_data": variation_data,
        "component_summary": dict(sorted(component_summary.items(), key=lambda x: abs(x[1]['total_diff']), reverse=True)),
        "staff_summary": staff_summary,
        "employees": Employee.objects.exclude(companyinformation__active_status='Inactive').order_by('lname'),
        "prev_month": prev_month,
        "prev_year": prev_year,
        "curr_month": curr_month,
        "curr_year": curr_year,
        "staffno": staffno,
        "component_type": component_type,
        "prev_date": prev_date.strftime('%B %Y') if prev_month else None,
        "curr_date": curr_date.strftime('%B %Y') if curr_month else None,
        "show_all": request.GET.get('show_all'),
    }
    
    return render(request, 'payroll/variation.html', context)


def export_component_variation_to_excel(variation_data, component_summary, staff_summary, 
                                       prev_date, curr_date, component_type, filename):
    """Export component variation analysis to Excel"""
    workbook_data = {}
    
    # Summary Sheet
    summary_rows = [
        {"Description": "STAFF SUMMARY", "Value": ""},
        {"Description": f"Total Staff ({prev_date.strftime('%b %Y')})", "Value": staff_summary['total_staff_prev']},
        {"Description": f"Total Staff ({curr_date.strftime('%b %Y')})", "Value": staff_summary['total_staff_curr']},
        {"Description": "Staff with Changes", "Value": staff_summary['staff_with_changes']},
        {"Description": f"New {component_type.title()}", "Value": staff_summary['new_components']},
        {"Description": f"Removed {component_type.title()}", "Value": staff_summary['removed_components']},
        {"Description": "", "Value": ""},
        {"Description": "AMOUNT SUMMARY", "Value": ""},
        {"Description": f"Total {prev_date.strftime('%b %Y')}", "Value": float(staff_summary['total_prev_amount'])},
        {"Description": f"Total {curr_date.strftime('%b %Y')}", "Value": float(staff_summary['total_curr_amount'])},
        {"Description": "Total Variation", "Value": float(staff_summary['total_variation'])},
        {"Description": "Variation %", "Value": calculate_percentage_change(staff_summary['total_prev_amount'], staff_summary['total_curr_amount'])},
    ]
    workbook_data["Summary"] = summary_rows
    
    # Component Summary Sheet
    component_rows = []
    for comp_type, data in sorted(component_summary.items(), key=lambda x: abs(x[1]['total_diff']), reverse=True):
        component_rows.append({
            f"{component_type.title()} Type": comp_type,
            f"{prev_date.strftime('%b %Y')} Total": float(data['total_prev']),
            f"{curr_date.strftime('%b %Y')} Total": float(data['total_curr']),
            "Difference": float(data['total_diff']),
            "% Change": data['percentage'],
            "Staff Affected": data['staff_count']
        })
    workbook_data[f"{component_type.title()} Summary"] = component_rows
    
    # Staff Details Sheet
    detail_rows = []
    for entry in variation_data:
        # Add staff header
        detail_rows.append({
            "Staff ID": entry['staff'].staffno if entry['staff'] else "Unknown",
            "Staff Name": f"{entry['staff'].fname} {entry['staff'].lname}" if entry['staff'] else "Unknown",
            "Department": entry['company_info'].dept if entry['company_info'] and entry['company_info'].dept else "-",
            f"{component_type.title()} Type": "",
            f"{prev_date.strftime('%b %Y')}": float(entry['total_prev']),
            f"{curr_date.strftime('%b %Y')}": float(entry['total_curr']),
            "Difference": float(entry['total_diff']),
            "% Change": entry['total_percentage'],
            "Status": "TOTAL"
        })
        
        # Add component details
        for var in entry['variations']:
            detail_rows.append({
                "Staff ID": "",
                "Staff Name": "",
                "Department": "",
                f"{component_type.title()} Type": var['type'],
                f"{prev_date.strftime('%b %Y')}": float(var['prev_amount']),
                f"{curr_date.strftime('%b %Y')}": float(var['curr_amount']),
                "Difference": float(var['difference']),
                "% Change": var['percentage'],
                "Status": var['status'].upper()
            })
        
        # Add empty row for spacing
        detail_rows.append({})
    
    workbook_data["Staff Details"] = detail_rows
    
    return render_to_excel(workbook_data, f"{filename}.xlsx")


def calculate_percentage_change(previous_amount, current_amount):
    if previous_amount is None or current_amount is None:
        return Decimal('0.00')
    
    prev = Decimal(str(previous_amount))
    curr = Decimal(str(current_amount))
    
    if prev == 0:
        if curr > 0:
            return Decimal('100.00')
        else:
            return Decimal('0.00')
    
    percentage = ((curr - prev) / prev) * 100
    return percentage.quantize(Decimal('0.01'))






###### HR REPORT ###########
# Academic rank mapping
ACADEMIC_RANKS = {
    'Professor': ['Professor'],
    'Associate Professor': ['Associate Professor'],
    'Senior Lecturer': ['Senior Lecturer'],
    'Lecturer': ['Lecturer'],
    'Assistant Lecturer': ['Assistant Lecturer'],
    'Tutor': ['Tutor']
}

# Qualification categories
QUALIFICATION_CATEGORIES = ['PHD', 'M.PHIL', 'MSc./M.A/M.Ed.', 'OTHERS']

AGE_BRACKETS = {
    "Below 30 Yrs.": (0, 29),
    "30 Yrs. - 40Yrs.": (30, 40),
    "41Yrs - 50Yrs.": (41, 50),
    "51 Yrs - 60 Yrs.": (51, 60),
    "Above 60 Yrs": (61, 200),
}

AGE_COLUMNS = [
    "Below 30 Yrs.",
    "30 Yrs. - 40Yrs.",
    "41Yrs - 50Yrs.",
    "51 Yrs - 60 Yrs.",
    "Above 60 Yrs"
]

def categorize_qualification(qualification):
    """Categorize qualification into standard categories"""
    if not qualification:
        return "OTHERS"
    
    qual_upper = str(qualification).upper()
    if 'PHD' in qual_upper or 'PH.D' in qual_upper:
        return 'PHD'
    elif 'M.PHIL' in qual_upper or 'MPHIL' in qual_upper:
        return 'M.PHIL'
    elif any(x in qual_upper for x in ['MSC', 'M.SC', 'MA', 'M.A', 'MED', 'M.ED', 'LLM']):
        # LLM mapped to MSc./M.A/M.Ed./LLM earlier -- but for table grouping we map it with the MSc/MA/M.Ed. group
        return 'MSc./M.A/M.Ed.'
    else:
        return 'OTHERS'

def get_academic_rank(staff):
    """Get academic rank from staff's company information"""
    company_info = CompanyInformation.objects.filter(staffno=staff).first()
    if company_info and company_info.rank:
        # If rank exactly matches a key keep it; otherwise default to 'Lecturer'
        return company_info.rank if company_info.rank in ACADEMIC_RANKS else 'Lecturer'
    return 'Lecturer'

def generate_academic_staff_table(school, dept, staff_qs):
    """Generate TABLE 17 format data"""
    data_rows = []
    
    # staff_matrix[gender][rank][qual_category] = count
    staff_matrix = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    
    for staff in staff_qs:
        # Normalize gender
        gender = staff.gender if staff.gender in ['Male', 'Female'] else 'Male'
        rank = get_academic_rank(staff)
        
        # Gather qualifications: heq + staff_school.certification entries
        qualifications = set()
        if getattr(staff, 'heq', None):
            qualifications.add(staff.heq)
        
        # Staff_School entries (many possible)
        staff_certs = Staff_School.objects.filter(staffno=staff)
        for cert in staff_certs:
            if cert.certification:
                qualifications.add(cert.certification)
        
        # If no qualifications found, mark as OTHERS / Bachelor placeholder
        if not qualifications:
            qualifications = {'OTHERS'}
        
        # Categorize and count
        for qual in qualifications:
            qual_category = categorize_qualification(qual)
            staff_matrix[gender][rank][qual_category] += 1
    
    # Build rows for Male and Female
    for gender in ['Male', 'Female']:
        row_data = {
            'FACULTY': school.sch_fac_name,
            'DEPARTMENT': dept.dept_long_name,
            'GENDER': gender[0],  # M or F
        }
        
        total_for_gender = 0
        # For each rank and qualification category, create a column
        for rank in ACADEMIC_RANKS.keys():
            for qual in QUALIFICATION_CATEGORIES:
                # column name formatting - keep it consistent and file-safe
                col_name = f"{rank}_{qual}".replace(' ', '_').replace('.', '').replace('/', '_')
                count = staff_matrix[gender][rank][qual]
                row_data[col_name] = count
                total_for_gender += count
        
        row_data['GRAND_TOTAL'] = total_for_gender
        
        # Include even if zero? your sample had 0 rows for genders with 0 - up to you.
        # We'll include only rows where there is at least one staff OR you can comment this condition out to include zeros
        if total_for_gender > 0:
            data_rows.append(row_data)
    
    # Add department total row (GENDER = 'T') summing columns across genders
    if data_rows:
        total_row = {
            'FACULTY': school.sch_fac_name,
            'DEPARTMENT': dept.dept_long_name,
            'GENDER': 'T',
        }
        grand_total = 0
        for rank in ACADEMIC_RANKS.keys():
            for qual in QUALIFICATION_CATEGORIES:
                col_name = f"{rank}_{qual}".replace(' ', '_').replace('.', '').replace('/', '_')
                total_count = sum(row.get(col_name, 0) for row in data_rows if row['DEPARTMENT'] == dept.dept_long_name)
                total_row[col_name] = total_count
                grand_total += total_count
        total_row['GRAND_TOTAL'] = grand_total
        data_rows.append(total_row)
    
    return data_rows
def generate_age_distribution_table(school, dept, staff_qs, today):
    """Generate TABLE 18 format data grouped by Gender and age brackets"""
    data_rows = []
    
    # age_matrix[gender][age_bracket] = count
    age_matrix = defaultdict(lambda: defaultdict(int))
    
    for staff in staff_qs:
        # if not getattr(staff, 'dob', None):
        #     continue
        
        gender = staff.gender if staff.gender in ['Male', 'Female'] else 'Male'
        age = (today - staff.dob).days // 365
        
        age_bracket = "Above 60 Yrs"  # default
        for label, (min_age, max_age) in AGE_BRACKETS.items():
            if min_age <= age <= max_age:
                age_bracket = label
                break
        
        age_matrix[gender][age_bracket] += 1
    
    # Build a row per gender if there is at least one count
    for gender in ['Male', 'Female']:
        # If gender has no counts, still include a zero row? Your sample shows zero rows for some genders.
        # We'll include rows only when total > 0 to avoid clutter; change if you want zeros included.
        total = sum(age_matrix[gender].values())
        if total == 0:
            # Still append zero row if you want it visible - comment out the continue to include zeros
            continue
        
        row_data = {
            'DEPARTMENT': dept.dept_long_name,
            'GENDER': gender,
        }
        grand = 0
        for age_col in AGE_COLUMNS:
            cnt = age_matrix[gender].get(age_col, 0)
            row_data[age_col] = cnt
            grand += cnt
        row_data['GRAND TOTAL'] = grand
        data_rows.append(row_data)
    
    return data_rows

def generate_department_report(request):
    """Main view: builds academic staff table and age distribution,
       writes both into one Excel sheet (Academic Staff Report)"""
    today = date.today()
    schools = School_Faculty.objects.all()
    
    academic_staff_data = []
    age_distribution_data = []
    
    for school in schools:
        departments = Department.objects.filter(sch_fac=school)
        
        for dept in departments:
            # only company info for this department; exclude inactive at company level
            company_info = CompanyInformation.objects.filter(dept=dept).exclude(active_status='Inactive')
            staff_ids = company_info.values_list("staffno_id", flat=True)
            
            # staff_qs - keep consistent with your existing code (uses staffno field)
            staff_qs = Employee.objects.filter(staffno__in=staff_ids)
            
            # If no staff, skip early
            if not staff_qs.exists():
                continue
            
            # Use all staff_qs as academic_staff (previous filtering caused empty set)
            academic_staff = staff_qs
            
            # Build TABLE 17 rows and extend master list
            dept_academic_rows = generate_academic_staff_table(school, dept, academic_staff)
            academic_staff_data.extend(dept_academic_rows)
            
            # Build TABLE 18 rows and extend master list
            dept_age_rows = generate_age_distribution_table(school, dept, academic_staff, today)
            age_distribution_data.extend(dept_age_rows)
    
    # Build DataFrames
    df_academic = pd.DataFrame(academic_staff_data)
    df_age = pd.DataFrame(age_distribution_data)
    
    # Prepare Excel response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="department_report.xlsx"'
    
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        sheet_name = "Academic Staff Report"
        # Write academic table first
        if not df_academic.empty:
            df_academic.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)
            start_row = len(df_academic) + 3
        else:
            start_row = 0
        
        # Add a small title above the age table for clarity
        if not df_age.empty:
            # write a title row (we write a one-row dataframe as title)
            title_df = pd.DataFrame([{"DEPARTMENT": "", "GENDER": "", **{c: "" for c in AGE_COLUMNS}, "GRAND TOTAL": ""}])
            # Instead of title_df, we can write a custom label; pandas ExcelWriter doesn't directly write raw text easily,
            # so we'll just leave the two blank rows and write the age table.
            df_age.to_excel(writer, sheet_name=sheet_name, index=False, startrow=start_row)
    
    return response
# =====================================================
# PAYROLL JOURNAL VIEWS
# =====================================================
@login_required
@role_required(['superadmin', 'finance admin'])
@tag_required('view_payroll_summary')
def payroll_summary(request):
    """
    Display overall payroll summary for a selected month
    """
    selected_month = request.GET.get("month")
    selected_year = request.GET.get("year")
    
    context = {
        'summary_data': None,
        'selected_month': selected_month,
        'selected_year': selected_year,
    }
    
    if selected_month and selected_year:
        # Create the date for the first day of the selected month
        selected_date = date(int(selected_year), int(selected_month), 28)
        
        # Get all approved payrolls for that month
        payrolls = Payroll.objects.filter(
            month=selected_date,
            is_approved=True
        )
        
        if payrolls.exists():
            # Calculate overall totals
            total_basic = payrolls.aggregate(Sum('basic_salary'))['basic_salary__sum'] or Decimal('0.00')
            total_gross = payrolls.aggregate(Sum('gross_salary'))['gross_salary__sum'] or Decimal('0.00')
            total_net = payrolls.aggregate(Sum('net_salary'))['net_salary__sum'] or Decimal('0.00')
            total_paye = payrolls.aggregate(Sum('income_tax'))['income_tax__sum'] or Decimal('0.00')
            total_ssf_employee = payrolls.aggregate(Sum('ssf_employee'))['ssf_employee__sum'] or Decimal('0.00')
            total_ssf_employer = payrolls.aggregate(Sum('ssf_employer'))['ssf_employer__sum'] or Decimal('0.00')
            total_pf_employee = payrolls.aggregate(Sum('pf_employee'))['pf_employee__sum'] or Decimal('0.00')
            total_pf_employer = payrolls.aggregate(Sum('pf_employer'))['pf_employer__sum'] or Decimal('0.00')
            total_other_deductions = payrolls.aggregate(Sum('other_deductions'))['other_deductions__sum'] or Decimal('0.00')
            total_relief = payrolls.aggregate(Sum('total_relief'))['total_relief__sum'] or Decimal('0.00')
            
            # Get all income types and their totals
            income_breakdown = {}
            for payroll in payrolls:
                for income in payroll.incomes.all():
                    if income.income_type and income.income_type.strip().lower() == 'basic salary':
                        continue
                    if income.income_type not in income_breakdown:
                        income_breakdown[income.income_type] = Decimal('0.00')
                    income_breakdown[income.income_type] += income.amount
            
            # Get all deduction types and their totals
            deduction_breakdown = {}
            for payroll in payrolls:
                for deduction in payroll.deductions.all():
                    if deduction.deduction_type not in deduction_breakdown:
                        deduction_breakdown[deduction.deduction_type] = Decimal('0.00')
                    deduction_breakdown[deduction.deduction_type] += deduction.amount

            # Extract statutory deductions that are displayed separately
            def extract_total(breakdown, predicate):
                total = Decimal('0.00')
                for original_key in list(breakdown.keys()):
                    normalized_key = (original_key or '').strip().lower()
                    if predicate(normalized_key):
                        total += breakdown.pop(original_key)
                return total

            # Remove standard statutory items from the "other deductions" list
            extract_total(deduction_breakdown, lambda key: key == 'income tax')
            extract_total(deduction_breakdown, lambda key: key.startswith('social security'))
            extract_total(deduction_breakdown, lambda key: key.startswith('provident fund'))
            total_wht_general = extract_total(deduction_breakdown, lambda key: key == 'withholding tax')
            total_wht_rent = extract_total(deduction_breakdown, lambda key: key == 'wht - rent')

            # Remaining deductions are displayed as detailed "Other Deductions"
            other_deductions_breakdown = OrderedDict(
                sorted(deduction_breakdown.items(), key=lambda item: item[0])
            )
            total_other_deductions = sum(other_deductions_breakdown.values(), Decimal('0.00'))
            
            staff_count = payrolls.count()
            
            # Check if journal has been generated for this month
            payroll_journal = PayrollJournal.objects.filter(month=selected_date).first()
            
            context['summary_data'] = {
                'month': selected_date,
                'staff_count': staff_count,
                'total_basic': total_basic,
                'total_gross': total_gross,
                'total_net': total_net,
                'total_paye': total_paye,
                'total_ssf_employee': total_ssf_employee,
                'total_ssf_employer': total_ssf_employer,
                'total_pf_employee': total_pf_employee,
                'total_pf_employer': total_pf_employer,
                'total_wht_general': total_wht_general,
                'total_wht_rent': total_wht_rent,
                'total_other_deductions': total_other_deductions,
                'total_relief': total_relief,
                'income_breakdown': income_breakdown,
                'deduction_breakdown': deduction_breakdown,
                'other_deductions_breakdown': other_deductions_breakdown,
                'payroll_journal': payroll_journal,
            }
    
    # Handle export
    export_format = request.GET.get("format")
    if export_format == "pdf" and context['summary_data']:
        return render_to_pdf("hr/payroll_summary.html", context, filename=f"payroll_summary_{selected_month}_{selected_year}.pdf")
    
    if export_format == "excel" and context['summary_data']:
        # Create Excel export
        data = context['summary_data']
        df_data = []
        
        # Basic summary
        df_data.append({'Description': 'Staff Count', 'Amount': data['staff_count']})
        df_data.append({'Description': 'Total Basic Salary', 'Amount': float(data['total_basic'])})
        
        # Income breakdown
        for income_type, amount in data['income_breakdown'].items():
            df_data.append({'Description': f'Total {income_type}', 'Amount': float(amount)})
        
        df_data.append({'Description': 'Total Gross Salary', 'Amount': float(data['total_gross'])})
        df_data.append({'Description': '', 'Amount': ''})  # Blank row
        
        # Deductions
        df_data.append({'Description': 'DEDUCTIONS', 'Amount': ''})
        df_data.append({'Description': 'Total PAYE', 'Amount': float(data['total_paye'])})
        df_data.append({'Description': 'Total SSF Employee', 'Amount': float(data['total_ssf_employee'])})
        df_data.append({'Description': 'Total PF Employee', 'Amount': float(data['total_pf_employee'])})
        if data['total_wht_general']:
            df_data.append({'Description': 'Total Withholding Tax', 'Amount': float(data['total_wht_general'])})
        if data['total_wht_rent']:
            df_data.append({'Description': 'Total WHT - Rent', 'Amount': float(data['total_wht_rent'])})
        if data['other_deductions_breakdown']:
            df_data.append({'Description': 'Other Deductions', 'Amount': ''})
            for deduction_type, amount in data['other_deductions_breakdown'].items():
                df_data.append({'Description': f'  {deduction_type}', 'Amount': float(amount)})
        df_data.append({'Description': 'Total Other Deductions', 'Amount': float(data['total_other_deductions'])})
        df_data.append({'Description': '', 'Amount': ''})  # Blank row
        
        # Employer contributions
        df_data.append({'Description': 'EMPLOYER CONTRIBUTIONS', 'Amount': ''})
        df_data.append({'Description': 'Total SSF Employer', 'Amount': float(data['total_ssf_employer'])})
        df_data.append({'Description': 'Total PF Employer', 'Amount': float(data['total_pf_employer'])})
        df_data.append({'Description': '', 'Amount': ''})  # Blank row
        
        df_data.append({'Description': 'Total Net Salary', 'Amount': float(data['total_net'])})
        
        df = pd.DataFrame(df_data)
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="payroll_summary_{selected_month}_{selected_year}.xlsx"'
        
        with pd.ExcelWriter(response, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Payroll Summary", index=False)
        
        return response
    
    return render(request, "hr/payroll_summary.html", context)


@login_required
@role_required(['superadmin', 'finance officer', 'finance admin', 'hr officer', 'hr admin'])
@tag_required('view_basic_salary_report')
def basic_salary_report(request):
    records = []
    total_basic = Decimal('0.00')

    company_infos = CompanyInformation.objects.filter(active_status__iexact='Active').select_related('staffno').order_by('staffno__staffno')

    for info in company_infos:
        staff = info.staffno
        salary_amount = safe_decimal(info.salary)
        name_parts = [staff.fname, staff.lname, staff.middlenames]
        display_name = " ".join(part for part in name_parts if part).strip() or staff.staffno

        records.append({
            'staffno': staff.staffno,
            'name': display_name,
            'amount': salary_amount,
        })
        total_basic += salary_amount

    export_format = request.GET.get("format")
    if export_format == "pdf" and records:
        filename_parts = "Basic Salary Report"
        filename = filename_parts + ".pdf"

        export_context = {
            'title': "Basic Salary Report",
            'records': records,
            'total': total_basic,
            'generated_on': timezone.now(),
        }
        return render_to_pdf("export/payroll_basic_salary.html", export_context, filename=filename)

    if export_format == "excel" and records:
        filename = "Basic Salary Report.xlsx"

        rows = []
        for record in records:
            rows.append({
                'Employee ID': record['staffno'],
                'Employee Name': record['name'],
                'Basic Salary': float(record['amount']),
            })

        return render_to_excel({"Basic Salary Report": rows}, filename=filename)

    context = {
        'records': records,
        'total_basic': total_basic,
        'record_count': len(records),
    }

    return render(request, "hr/basic_salary_report.html", context)

@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('setup_payroll_account_mapping')
def payroll_account_mapping(request):
    """
    Setup page for mapping payroll items to GL accounts
    """
    from ledger.models import Account
    
    if request.method == "POST":
        account_type = request.POST.get('account_type')
        sub_type = request.POST.get('sub_type', '')
        debit_account_id = request.POST.get('debit_account')
        credit_account_id = request.POST.get('credit_account')
        description_template = request.POST.get('description_template')
        
        debit_account = Account.objects.get(id=debit_account_id) if debit_account_id else None
        credit_account = Account.objects.get(id=credit_account_id) if credit_account_id else None
        
        # Create or update mapping
        mapping, created = PayrollAccountMapping.objects.update_or_create(
            account_type=account_type,
            sub_type=sub_type if sub_type else None,
            defaults={
                'debit_account': debit_account,
                'credit_account': credit_account,
                'description_template': description_template,
                'created_by': request.user,
            }
        )
        
        messages.success(request, f"Mapping for {mapping} has been {'created' if created else 'updated'} successfully!")
        logger.info(f"User {request.user} {'created' if created else 'updated'} payroll account mapping: {mapping}")
        
        return redirect('payroll-account-mapping')
    
    # Get all accounts for dropdown
    accounts = Account.objects.filter(type__in=['ASSET', 'LIABILITY', 'EXPENSE']).order_by('code')
    mappings = PayrollAccountMapping.objects.all()
    
    # Get all income types (allowances) from IncomeType configuration table
    all_income_types = IncomeType.objects.values_list('name', flat=True).order_by('name')
    # Exclude "Basic Salary" from allowances as it has its own mapping
    available_allowances = [inc for inc in all_income_types if inc and inc.lower() != 'basic salary']
    
    # Get all deduction types from DeductionType configuration table
    all_deduction_types = DeductionType.objects.values_list('name', flat=True).order_by('name')
    # Exclude statutory deductions (they have their own mappings)
    statutory_deductions = ['income tax', 'social security', 'provident fund']
    regular_deductions = [
        ded for ded in all_deduction_types 
        if ded and not any(stat_ded in ded.lower() for stat_ded in statutory_deductions)
    ]
    
    # Get all loan types from ChoicesLoanType configuration table
    loan_types = list(ChoicesLoanType.objects.values_list('name', flat=True).order_by('name'))
    
    # Get all medical surcharge types from ChoicesMedicalTreatment configuration table
    # Format: "Medical Surcharge {treatment_type}"
    medical_treatments = ChoicesMedicalTreatment.objects.values_list('name', flat=True).order_by('name')
    medical_surcharge_types = [f"Medical Surcharge {treatment}" for treatment in medical_treatments]
    
    # Special statutory deductions calculated automatically
    # withholding_types = ['Withholding Tax', 'WHT - Rent']
    
    # Combine all deduction types and remove duplicates while preserving order
    all_deductions = list(regular_deductions) + loan_types + medical_surcharge_types
    # Remove duplicates while preserving order
    seen = set()
    available_deductions = []
    for ded in all_deductions:
        if ded not in seen:
            seen.add(ded)
            available_deductions.append(ded)
    
    accounts_for_js = [
        {
            'id': account.id,
            'code': account.code,
            'name': account.name,
            'display': f"{account.code} - {account.name}",
        }
        for account in accounts
    ]
    
    account_requirements = {
        'basic_salary': {'requires_debit': True, 'requires_credit': False},
        'allowance': {'requires_debit': True, 'requires_credit': False},
        'ssf_employee': {'requires_debit': False, 'requires_credit': True},
        'ssf_employer': {'requires_debit': True, 'requires_credit': False},
        'pf_employee': {'requires_debit': False, 'requires_credit': True},
        'pf_employer': {'requires_debit': True, 'requires_credit': True},
        'paye': {'requires_debit': False, 'requires_credit': True},
        'wht_general': {'requires_debit': False, 'requires_credit': True},
        'wht_rent': {'requires_debit': False, 'requires_credit': True},
        'other_deduction': {'requires_debit': False, 'requires_credit': True},
        'net_salary': {'requires_debit': False, 'requires_credit': True},
    }
    
    context = {
        'accounts': accounts,
        'accounts_for_js': accounts_for_js,
        'mappings': mappings,
        'account_type_choices': PayrollAccountMapping.ACCOUNT_TYPE_CHOICES,
        'available_allowances': available_allowances,
        'available_deductions': available_deductions,
        'loan_types': loan_types,
        'medical_surcharge_types': medical_surcharge_types,
        'account_requirements': account_requirements,
    }
    
    return render(request, "hr/payroll_account_mapping.html", context)


@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
def delete_payroll_mapping(request, mapping_id):
    """Delete a payroll account mapping"""
    mapping = get_object_or_404(PayrollAccountMapping, id=mapping_id)
    mapping.delete()
    messages.success(request, f"Mapping deleted successfully!")
    logger.info(f"User {request.user} deleted payroll account mapping: {mapping}")
    return redirect('payroll-account-mapping')


@login_required
@role_required(['superadmin', 'finance officer', 'finance admin'])
@tag_required('preview_payroll_journal')
def preview_payroll_journal(request):
    """
    Preview the journal entries that will be created for a specific payroll month
    """
    
    selected_month = request.GET.get("month")
    selected_year = request.GET.get("year")
    
    context = {
        'preview_data': None,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'errors': [],
    }
    
    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 28)
        month_str = month_name[int(selected_month)]
        
        # Check if journal already exists
        existing_journal = PayrollJournal.objects.filter(month=selected_date).first()
        if existing_journal:
            context['errors'].append(f"A journal has already been generated for {month_str} {selected_year}.")
            context['existing_journal'] = existing_journal
            if existing_journal.journal:
                context['existing_journal_status'] = existing_journal.journal.status
                context['existing_journal_id'] = existing_journal.journal.id
            context['existing_is_posted'] = existing_journal.is_posted
            return render(request, "hr/preview_payroll_journal.html", context)
        
        # Get all approved payrolls for that month
        payrolls = Payroll.objects.filter(
            month=selected_date,
            is_approved=True
        )
        
        if not payrolls.exists():
            context['errors'].append(f"No approved payrolls found for {month_str} {selected_year}.")
            return render(request, "hr/preview_payroll_journal.html", context)
        
        # Check if all required mappings are set up
        required_mappings = ['basic_salary', 'ssf_employee', 'ssf_employer', 'pf_employee', 'pf_employer', 'paye', 'net_salary']
        missing_mappings = []
        
        for mapping_type in required_mappings:
            mapping = PayrollAccountMapping.objects.filter(account_type=mapping_type, is_active=True).first()
            if not mapping or not mapping.debit_account or not mapping.credit_account:
                missing_mappings.append(mapping_type.replace('_', ' ').title())
        
        if missing_mappings:
            context['errors'].append(f"Missing account mappings for: {', '.join(missing_mappings)}. Please configure them first.")
            return render(request, "hr/preview_payroll_journal.html", context)
        
        # Calculate all totals
        total_basic = payrolls.aggregate(Sum('basic_salary'))['basic_salary__sum'] or Decimal('0.00')
        total_paye = payrolls.aggregate(Sum('income_tax'))['income_tax__sum'] or Decimal('0.00')
        total_ssf_employee = payrolls.aggregate(Sum('ssf_employee'))['ssf_employee__sum'] or Decimal('0.00')
        total_ssf_employer = payrolls.aggregate(Sum('ssf_employer'))['ssf_employer__sum'] or Decimal('0.00')
        total_pf_employee = payrolls.aggregate(Sum('pf_employee'))['pf_employee__sum'] or Decimal('0.00')
        total_pf_employer = payrolls.aggregate(Sum('pf_employer'))['pf_employer__sum'] or Decimal('0.00')
        
        total_wht_general = PayrollDeduction.objects.filter(
            payroll__in=payrolls,
            deduction_type='Withholding Tax'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        total_wht_rent = PayrollDeduction.objects.filter(
            payroll__in=payrolls,
            deduction_type='WHT - Rent'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        total_other_deductions = payrolls.aggregate(Sum('other_deductions'))['other_deductions__sum'] or Decimal('0.00')
        total_net = payrolls.aggregate(Sum('net_salary'))['net_salary__sum'] or Decimal('0.00')
        
        # Get all income types and their totals (allowances) - each separately
        # Exclude "Basic Salary" as it's handled separately
        income_breakdown = {}
        for payroll in payrolls:
            for income in payroll.incomes.all():
                # Skip "Basic Salary" as it's already handled separately
                if income.income_type.lower() == 'basic salary':
                    continue
                if income.income_type not in income_breakdown:
                    income_breakdown[income.income_type] = Decimal('0.00')
                income_breakdown[income.income_type] += income.amount
        
        # Get all deduction types and their totals - each separately (matching hard copy format)
        # Exclude statutory deductions (Income Tax, SSF, PF) as they're handled separately
        statutory_deductions = ['income tax', 'social security', 'provident fund', 'withholding tax', 'wht - rent']
        deduction_breakdown = {}
        for payroll in payrolls:
            for deduction in payroll.deductions.all():
                # Skip statutory deductions as they're handled separately
                deduction_lower = deduction.deduction_type.lower()
                if any(stat_ded in deduction_lower for stat_ded in statutory_deductions):
                    continue
                if deduction.deduction_type not in deduction_breakdown:
                    deduction_breakdown[deduction.deduction_type] = Decimal('0.00')
                deduction_breakdown[deduction.deduction_type] += deduction.amount
        
        # Build journal line preview - matching hard copy format
        all_lines = []
        line_number = 1
        
        # DEBIT: Consolidated Basic Salary (Line 1)
        basic_mapping = PayrollAccountMapping.objects.get(account_type='basic_salary', is_active=True)
        all_lines.append({
            'line_number': line_number,
            'account': basic_mapping.debit_account,
            'description': basic_mapping.description_template.format(month=month_str, year=selected_year),
            'debit': total_basic,
            'credit': Decimal('0.00'),
        })
        line_number += 1
        
        # DEBIT: All allowances (incomes) - each as separate line (matching hard copy)
        for income_type, amount in sorted(income_breakdown.items()):
            if amount > 0:  # Only include if amount > 0
                # Try to find specific mapping for this allowance
                allowance_mapping = PayrollAccountMapping.objects.filter(
                    account_type='allowance',
                    sub_type=income_type,
                    is_active=True
                ).first()
                
                if allowance_mapping and allowance_mapping.debit_account:
                    all_lines.append({
                        'line_number': line_number,
                        'account': allowance_mapping.debit_account,
                        'description': income_type,  # Use the income type name directly
                        'debit': amount,
                        'credit': Decimal('0.00'),
                    })
                    line_number += 1
                else:
                    # Use generic allowance mapping or create a default one
                    generic_mapping = PayrollAccountMapping.objects.filter(
                        account_type='allowance',
                        sub_type__isnull=True,
                        is_active=True
                    ).first()
                    if generic_mapping and generic_mapping.debit_account:
                        all_lines.append({
                            'line_number': line_number,
                            'account': generic_mapping.debit_account,
                            'description': income_type,
                            'debit': amount,
                            'credit': Decimal('0.00'),
                        })
                        line_number += 1
                    else:
                        context['errors'].append(f"No mapping found for allowance: {income_type}. Please set it up in Account Mapping.")
        
        # DEBIT: Employer contributions - separate lines
        if total_ssf_employer > 0:
            ssf_employer_mapping = PayrollAccountMapping.objects.get(account_type='ssf_employer', is_active=True)
            all_lines.append({
                'line_number': line_number,
                'account': ssf_employer_mapping.debit_account,
                'description': ssf_employer_mapping.description_template.format(month=month_str, year=selected_year),
                'debit': total_ssf_employer,
                'credit': Decimal('0.00'),
            })
            line_number += 1
        
        if total_pf_employer > 0:
            pf_employer_mapping = PayrollAccountMapping.objects.get(account_type='pf_employer', is_active=True)
            all_lines.append({
                'line_number': line_number,
                'account': pf_employer_mapping.debit_account,
                'description': "Provident Fund-Employer",
                'debit': total_pf_employer,
                'credit': Decimal('0.00'),
            })
            line_number += 1
        
        # CREDIT: SSF (Total = Employee + Employer combined)
        total_ssf = total_ssf_employee + total_ssf_employer
        if total_ssf > 0:
            ssf_employee_mapping = PayrollAccountMapping.objects.get(account_type='ssf_employee', is_active=True)
            all_lines.append({
                'line_number': line_number,
                'account': ssf_employee_mapping.credit_account,
                'description': f"S.S.F (13%)",
                'debit': Decimal('0.00'),
                'credit': total_ssf,
            })
            line_number += 1
        
        # CREDIT: PAYE / Income Tax
        if total_paye > 0:
            paye_mapping = PayrollAccountMapping.objects.get(account_type='paye', is_active=True)
            all_lines.append({
                'line_number': line_number,
                'account': paye_mapping.credit_account,
                'description': "Income Tax",
                'debit': Decimal('0.00'),
                'credit': total_paye,
            })
            line_number += 1
        
        # CREDIT: PF Employee (separate line)
        if total_pf_employee > 0:
            pf_employee_mapping = PayrollAccountMapping.objects.get(account_type='pf_employee', is_active=True)
            all_lines.append({
                'line_number': line_number,
                'account': pf_employee_mapping.credit_account,
                'description': "Provident Fund-Employee",
                'debit': Decimal('0.00'),
                'credit': total_pf_employee,
            })
            line_number += 1
        
        if total_pf_employer > 0:
            pf_employer_credit_mapping = PayrollAccountMapping.objects.get(account_type='pf_employer', is_active=True)
            all_lines.append({
                'line_number': line_number,
                'account': pf_employer_credit_mapping.credit_account,
                'description': "Provident Fund-Employer",
                'debit': Decimal('0.00'),
                'credit': total_pf_employer,
            })
            line_number += 1
            
            
        # CREDIT: Withholding Tax (Non-rent)
        if total_wht_general > 0:
            wht_general_mapping = PayrollAccountMapping.objects.get(account_type='wht_general', is_active=True)
            all_lines.append({
                'line_number': line_number,
                'account': wht_general_mapping.credit_account,
                'description': wht_general_mapping.description_template.format(month=month_str, year=selected_year),
                'debit': Decimal('0.00'),
                'credit': total_wht_general,
            })
            line_number += 1
        
        # CREDIT: Withholding Tax (Rent)
        if total_wht_rent > 0:
            wht_rent_mapping = PayrollAccountMapping.objects.get(account_type='wht_rent', is_active=True)
            all_lines.append({
                'line_number': line_number,
                'account': wht_rent_mapping.credit_account,
                'description': wht_rent_mapping.description_template.format(month=month_str, year=selected_year),
                'debit': Decimal('0.00'),
                'credit': total_wht_rent,
            })
            line_number += 1
        
        # CREDIT: All other deductions - each as separate line (matching hard copy format)
        for deduction_type, amount in sorted(deduction_breakdown.items()):
            if amount > 0:  # Only include if amount > 0
                # Try to find specific mapping for this deduction
                deduction_mapping = PayrollAccountMapping.objects.filter(
                    account_type='other_deduction',
                    sub_type=deduction_type,
                    is_active=True
                ).first()
                
                if deduction_mapping and deduction_mapping.credit_account:
                    all_lines.append({
                        'line_number': line_number,
                        'account': deduction_mapping.credit_account,
                        'description': deduction_type,  # Use the deduction type name directly
                        'debit': Decimal('0.00'),
                        'credit': amount,
                    })
                    line_number += 1
                else:
                    # Use generic other deduction mapping
                    generic_deduction_mapping = PayrollAccountMapping.objects.filter(
                        account_type='other_deduction',
                        sub_type__isnull=True,
                        is_active=True
                    ).first()
                    if generic_deduction_mapping and generic_deduction_mapping.credit_account:
                        all_lines.append({
                            'line_number': line_number,
                            'account': generic_deduction_mapping.credit_account,
                            'description': deduction_type,
                            'debit': Decimal('0.00'),
                            'credit': amount,
                        })
                        line_number += 1
                    else:
                        context['errors'].append(f"No mapping found for deduction: {deduction_type}. Please set it up in Account Mapping.")
        
        # CREDIT: Net Salary Payable (Bank/Cash Payment)
        if total_net > 0:
            net_salary_mapping = PayrollAccountMapping.objects.get(account_type='net_salary', is_active=True)
            all_lines.append({
                'line_number': line_number,
                'account': net_salary_mapping.credit_account,
                'description': "Total Net Salary (Bank/Cash Payment)",
                'debit': Decimal('0.00'),
                'credit': total_net,
            })
            line_number += 1
        
        # Calculate totals
        total_debits = sum(line['debit'] for line in all_lines)
        total_credits = sum(line['credit'] for line in all_lines)
        
        context['preview_data'] = {
            'month': selected_date,
            'month_name': month_str,
            'year': selected_year,
            'reference': f"PAYROLL-{month_str.upper()}-{selected_year}",
            'staff_count': payrolls.count(),
            'journal_lines': all_lines,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'is_balanced': total_debits == total_credits,
            'auto_submit': True,
        }
    
    return render(request, "hr/preview_payroll_journal.html", context)


@login_required
@role_required(['superadmin', 'finance admin'])
@tag_required('generate_payroll_journal')
@transaction.atomic
def generate_payroll_journal(request):
    """
    Generate and post the journal entry for a specific payroll month
    """
    
    if request.method != "POST":
        return redirect('preview-payroll-journal')
    
    selected_month = request.POST.get("month")
    selected_year = request.POST.get("year")
    
    if not selected_month or not selected_year:
        messages.error(request, "Please select a month and year.")
        return redirect('preview-payroll-journal')
    
    selected_date = date(int(selected_year), int(selected_month), 1)
    month_str = month_name[int(selected_month)]
    
    # Check if journal already exists
    existing_journal = PayrollJournal.objects.filter(month=selected_date).first()
    if existing_journal:
        messages.error(request, f"A journal has already been generated for {month_str} {selected_year}.")
        return redirect('payroll-journal-history')
    
    # Get all approved payrolls for that month
    payrolls = Payroll.objects.filter(
        month=selected_date,
        is_approved=True
    )
    
    if not payrolls.exists():
        messages.error(request, f"No approved payrolls found for {month_str} {selected_year}.")
        return redirect('preview-payroll-journal')
    
    try:
        # Calculate all totals
        total_basic = payrolls.aggregate(Sum('basic_salary'))['basic_salary__sum'] or Decimal('0.00')
        total_paye = payrolls.aggregate(Sum('income_tax'))['income_tax__sum'] or Decimal('0.00')
        total_ssf_employee = payrolls.aggregate(Sum('ssf_employee'))['ssf_employee__sum'] or Decimal('0.00')
        total_ssf_employer = payrolls.aggregate(Sum('ssf_employer'))['ssf_employer__sum'] or Decimal('0.00')
        total_pf_employee = payrolls.aggregate(Sum('pf_employee'))['pf_employee__sum'] or Decimal('0.00')
        total_pf_employer = payrolls.aggregate(Sum('pf_employer'))['pf_employer__sum'] or Decimal('0.00')
        
        total_wht_general = PayrollDeduction.objects.filter(
            payroll__in=payrolls,
            deduction_type='Withholding Tax'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        total_wht_rent = PayrollDeduction.objects.filter(
            payroll__in=payrolls,
            deduction_type='WHT - Rent'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        total_other_deductions = payrolls.aggregate(Sum('other_deductions'))['other_deductions__sum'] or Decimal('0.00')
        total_net = payrolls.aggregate(Sum('net_salary'))['net_salary__sum'] or Decimal('0.00')
        
        # Get all income types and their totals (allowances) - each separately
        # Exclude "Basic Salary" as it's handled separately
        income_breakdown = {}
        for payroll in payrolls:
            for income in payroll.incomes.all():
                # Skip "Basic Salary" as it's already handled separately
                if income.income_type.lower() == 'basic salary':
                    continue
                if income.income_type not in income_breakdown:
                    income_breakdown[income.income_type] = Decimal('0.00')
                income_breakdown[income.income_type] += income.amount
        
        # Get all deduction types and their totals - each separately (matching hard copy format)
        # Exclude statutory deductions (Income Tax, SSF, PF) as they're handled separately
        statutory_deductions = ['income tax', 'social security', 'provident fund', 'withholding tax', 'wht - rent']
        deduction_breakdown = {}
        for payroll in payrolls:
            for deduction in payroll.deductions.all():
                # Skip statutory deductions as they're handled separately
                deduction_lower = deduction.deduction_type.lower()
                if any(stat_ded in deduction_lower for stat_ded in statutory_deductions):
                    continue
                if deduction.deduction_type not in deduction_breakdown:
                    deduction_breakdown[deduction.deduction_type] = Decimal('0.00')
                deduction_breakdown[deduction.deduction_type] += deduction.amount
        
        # Get the last day of the month for journal date
        last_day = monthrange(int(selected_year), int(selected_month))[1]
        journal_date = date(int(selected_year), int(selected_month), last_day)
        
        # Create the journal entry
        reference = f"PAYROLL-{month_str.upper()}-{selected_year}"
        base_currency = Currency.objects.filter(is_base_currency=True).first()
        journal = Journal.objects.create(
            reference=reference,
            date=journal_date,
            description=f"CONSOLIDATED PAYROLL JOURNAL FOR {month_str}, {selected_year}",
            source_module='PAYROLL',
            status='DRAFT',
            created_by=request.user,
        )
        
        # Create PayrollJournal record
        payroll_journal = PayrollJournal.objects.create(
            month=selected_date,
            journal=journal,
            reference=reference,
            staff_count=payrolls.count(),
            is_posted=False,
            created_by=request.user,
        )
        
        # DEBIT LINES - matching hard copy format
        line_number = 1
        
        # DEBIT: Consolidated Basic Salary
        basic_mapping = PayrollAccountMapping.objects.get(account_type='basic_salary', is_active=True)
        JournalLine.objects.create(
            journal=journal,
            line_number=line_number,
            account=basic_mapping.debit_account,
            description=basic_mapping.description_template.format(month=month_str, year=selected_year),
            debit=total_basic,
            credit=Decimal('0.00'),
            date=journal_date,
            currency=base_currency,
            exchange_rate=Decimal('1.0'),
        )
        line_number += 1
        
        # DEBIT: All allowances (incomes) - each as separate line
        for income_type, amount in sorted(income_breakdown.items()):
            if amount > 0:
                allowance_mapping = PayrollAccountMapping.objects.filter(
                    account_type='allowance',
                    sub_type=income_type,
                    is_active=True
                ).first()
                
                if allowance_mapping and allowance_mapping.debit_account:
                    JournalLine.objects.create(
                        journal=journal,
                        line_number=line_number,
                        account=allowance_mapping.debit_account,
                        description=income_type,  # Use income type name directly
                        debit=amount,
                        credit=Decimal('0.00'),
                        date=journal_date,
                        currency=base_currency,
                        exchange_rate=Decimal('1.0'),
                    )
                    line_number += 1
                else:
                    # Try generic allowance mapping
                    generic_mapping = PayrollAccountMapping.objects.filter(
                        account_type='allowance',
                        sub_type__isnull=True,
                        is_active=True
                    ).first()
                    if generic_mapping and generic_mapping.debit_account:
                        JournalLine.objects.create(
                            journal=journal,
                            line_number=line_number,
                            account=generic_mapping.debit_account,
                            description=income_type,
                            debit=amount,
                            credit=Decimal('0.00'),
                            date=journal_date,
                            currency=base_currency,
                            exchange_rate=Decimal('1.0'),
                        )
                        line_number += 1
        
        # DEBIT: Employer contributions - separate lines
        if total_ssf_employer > 0:
            ssf_employer_mapping = PayrollAccountMapping.objects.get(account_type='ssf_employer', is_active=True)
            JournalLine.objects.create(
                journal=journal,
                line_number=line_number,
                account=ssf_employer_mapping.debit_account,
                description=ssf_employer_mapping.description_template.format(month=month_str, year=selected_year),
                debit=total_ssf_employer,
                credit=Decimal('0.00'),
                date=journal_date,
                currency=base_currency,
                exchange_rate=Decimal('1.0'),
            )
            line_number += 1
        
        if total_pf_employer > 0:
            pf_employer_mapping = PayrollAccountMapping.objects.get(account_type='pf_employer', is_active=True)
            JournalLine.objects.create(
                journal=journal,
                line_number=line_number,
                account=pf_employer_mapping.debit_account,
                description="Provident Fund-Employer",
                debit=total_pf_employer,
                credit=Decimal('0.00'),
                date=journal_date,
                currency=base_currency,
                exchange_rate=Decimal('1.0'),
            )
            line_number += 1
        
        # CREDIT LINES
        
        # CREDIT: SSF (Total = Employee + Employer combined)
        total_ssf = total_ssf_employee + total_ssf_employer
        if total_ssf > 0:
            ssf_employee_mapping = PayrollAccountMapping.objects.get(account_type='ssf_employee', is_active=True)
            JournalLine.objects.create(
                journal=journal,
                line_number=line_number,
                account=ssf_employee_mapping.credit_account,
                description="S.S.F (13%)",
                debit=Decimal('0.00'),
                credit=total_ssf,
                date=journal_date,
                currency=base_currency,
                exchange_rate=Decimal('1.0'),
            )
            line_number += 1
        
        # CREDIT: PAYE / Income Tax
        if total_paye > 0:
            paye_mapping = PayrollAccountMapping.objects.get(account_type='paye', is_active=True)
            JournalLine.objects.create(
                journal=journal,
                line_number=line_number,
                account=paye_mapping.credit_account,
                description="Income Tax",
                debit=Decimal('0.00'),
                credit=total_paye,
                date=journal_date,
                currency=base_currency,
                exchange_rate=Decimal('1.0'),
            )
            line_number += 1
        
        # CREDIT: PF Employee (separate line)
        if total_pf_employee > 0:
            pf_employee_mapping = PayrollAccountMapping.objects.get(account_type='pf_employee', is_active=True)
            JournalLine.objects.create(
                journal=journal,
                line_number=line_number,
                account=pf_employee_mapping.credit_account,
                description="Provident Fund-Employee",
                debit=Decimal('0.00'),
                credit=total_pf_employee,
                date=journal_date,
                currency=base_currency,
                exchange_rate=Decimal('1.0'),
            )
            line_number += 1
        
        if total_pf_employer > 0:
            pf_employer_credit_mapping = PayrollAccountMapping.objects.get(account_type='pf_employer', is_active=True)
            JournalLine.objects.create(
                journal=journal,
                line_number=line_number,
                account=pf_employer_credit_mapping.credit_account,
                description="Provident Fund-Employer",
                debit=Decimal('0.00'),
                credit=total_pf_employer,
                date=journal_date,
                currency=base_currency,
                exchange_rate=Decimal('1.0'),
            )
            line_number += 1
        
        # CREDIT: Withholding Tax (Non-rent)
        if total_wht_general > 0:
            wht_general_mapping = PayrollAccountMapping.objects.get(account_type='wht_general', is_active=True)
            JournalLine.objects.create(
                journal=journal,
                line_number=line_number,
                account=wht_general_mapping.credit_account,
                description=wht_general_mapping.description_template.format(month=month_str, year=selected_year),
                debit=Decimal('0.00'),
                credit=total_wht_general,
                date=journal_date,
                currency=base_currency,
                exchange_rate=Decimal('1.0'),
            )
            line_number += 1
        
        # CREDIT: Withholding Tax (Rent)
        if total_wht_rent > 0:
            wht_rent_mapping = PayrollAccountMapping.objects.get(account_type='wht_rent', is_active=True)
            JournalLine.objects.create(
                journal=journal,
                line_number=line_number,
                account=wht_rent_mapping.credit_account,
                description=wht_rent_mapping.description_template.format(month=month_str, year=selected_year),
                debit=Decimal('0.00'),
                credit=total_wht_rent,
                date=journal_date,
                currency=base_currency,
                exchange_rate=Decimal('1.0'),
            )
            line_number += 1
        
        # CREDIT: All other deductions - each as separate line (matching hard copy format)
        for deduction_type, amount in sorted(deduction_breakdown.items()):
            if amount > 0:
                deduction_mapping = PayrollAccountMapping.objects.filter(
                    account_type='other_deduction',
                    sub_type=deduction_type,
                    is_active=True
                ).first()
                
                if deduction_mapping and deduction_mapping.credit_account:
                    JournalLine.objects.create(
                        journal=journal,
                        line_number=line_number,
                        account=deduction_mapping.credit_account,
                        description=deduction_type,  # Use deduction type name directly
                        debit=Decimal('0.00'),
                        credit=amount,
                        date=journal_date,
                        currency=base_currency,
                        exchange_rate=Decimal('1.0'),
                    )
                    line_number += 1
                else:
                    # Try generic deduction mapping
                    generic_deduction_mapping = PayrollAccountMapping.objects.filter(
                        account_type='other_deduction',
                        sub_type__isnull=True,
                        is_active=True
                    ).first()
                    if generic_deduction_mapping and generic_deduction_mapping.credit_account:
                        JournalLine.objects.create(
                            journal=journal,
                            line_number=line_number,
                            account=generic_deduction_mapping.credit_account,
                            description=deduction_type,
                            debit=Decimal('0.00'),
                            credit=amount,
                            date=journal_date,
                            currency=base_currency,
                            exchange_rate=Decimal('1.0'),
                        )
                        line_number += 1
        
        # CREDIT: Net Salary Payable (Bank/Cash Payment)
        if total_net > 0:
            net_salary_mapping = PayrollAccountMapping.objects.get(account_type='net_salary', is_active=True)
            JournalLine.objects.create(
                journal=journal,
                line_number=line_number,
                account=net_salary_mapping.credit_account,
                description="Total Net Salary (Bank/Cash Payment)",
                debit=Decimal('0.00'),
                credit=total_net,
                date=journal_date,
                currency=base_currency,
                exchange_rate=Decimal('1.0'),
            )
            line_number += 1
        
        # Calculate and update totals
        journal_lines = journal.lines.all()
        total_debits = sum(line.debit for line in journal_lines)
        total_credits = sum(line.credit for line in journal_lines)
        
        payroll_journal.total_debit = total_debits
        payroll_journal.total_credit = total_credits
        payroll_journal.save()
        
        # Submit journal for approval (auto-submit) and log approval entry
        try:
            journal.submit_for_approval(request.user)
        except ValidationError as ve:
            messages.error(request, ve)
            raise

        # Update all payrolls to mark as journalized
        payrolls.update(is_journalized=True, payroll_journal=payroll_journal)

        messages.success(request, f"Payroll journal for {month_str} {selected_year} has been generated and submitted for approval.")
        logger.info(f"User {request.user} generated payroll journal (pending approval): {reference}")

        return redirect('payroll-journal-history')
        
    except Exception as e:
        messages.error(request, f"Error generating journal: {str(e)}")
        logger.error(f"Error generating payroll journal: {str(e)}")
        return redirect('preview-payroll-journal')


@login_required
@role_required(['superadmin', 'finance admin'])
@tag_required('view_payroll_journal_history')
def payroll_journal_history(request):
    """
    View all generated payroll journals
    """
    journals = PayrollJournal.objects.select_related(
        'journal',
        'journal__created_by',
        'journal__submitted_by',
        'journal__approved_by',
        'journal__posted_by'
    ).order_by('-month')
    
    # Filter by month/year if provided
    selected_month = request.GET.get("month")
    selected_year = request.GET.get("year")
    
    if selected_month and selected_year:
        selected_date = date(int(selected_year), int(selected_month), 1)
        journals = journals.filter(month=selected_date)
    
    context = {
        'journals': journals,
        'selected_month': selected_month,
        'selected_year': selected_year,
    }
    
    return render(request, "hr/payroll_journal_history.html", context)


@login_required
def user_manual(request):
    """
    Display the user manual in the application
    """
    import os
    
    manual_path = os.path.join(settings.BASE_DIR, 'USER_MANUAL.md')
    
    try:
        import markdown
    except ImportError:
        html_content = (
            "<h3>Markdown library is not installed. "
            "Please install the 'markdown' package from requirement.txt.</h3>"
        )
    else:
        try:
            with open(manual_path, 'r', encoding='utf-8') as f:
                manual_content = f.read()
                # Convert markdown to HTML
                html_content = markdown.markdown(manual_content, extensions=['tables', 'fenced_code'])
        except FileNotFoundError:
            html_content = "<h3>User Manual not found. Please contact your administrator.</h3>"
    
    context = {
        'manual_content': html_content,
    }
    
    return render(request, "hr/user_manual.html", context)