from django.http import HttpResponseRedirect # type: ignore
from django.shortcuts import redirect, render # type: ignore
from .forms import *
from .choices import *
from .models import *
from setup.models import *
from django.db import connection # type: ignore
# Create your views here.
def index(request):
    return render(request,'authentication/login.html',{})

def register(request):
    return render(request,'authentication/register.html',{})

def landing(request):
    return render(request,'hr/landing_page.html',{})

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
    return render(request,'hr/staff_data.html',{'staff':staff,'schools':schools})

def edit_staff(request,staffno):
    # q = q.exclude(body_text__icontains="food")
    staffs = Employee.objects.order_by('lname').filter(active_status__exact='Active') 
    staff_count = staffs.count()
    staff = Employee.objects.get(pk=staffno)
    form = EmployeeForm(request.POST or None,request.FILES or None,instance=staff)
    if request.method == 'POST':
        # form = EmployeeForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            return redirect('newstaff')
        
    context = {
                'form':form,
            #    'submitted':submitted,
               'staffs':staffs,
               'staff_count':staff_count,
               'RBA':RBA,
               'STAFFLEVEL':STAFFLEVEL,
               'STAFFSTATUS':STAFFSTATUS,
               'STAFFRANK':STAFFRANK,
               'GENDER':GENDER,
               'DEPENDANTS':DEPENDANTS,
               'HEQ':HEQ,
               'REGION':REGION,
               'TITLE':TITLE,
               'SUFFIX':SUFFIX,
               'staff':staff,
               }

    # context = {'form':form,'staffs':staffs,'staff_count':staff_count,'staff':staff}
    return render(request, 'hr/new_staff.html', context)

def newstaff(request):
    submitted = False
    staffs = Employee.objects.order_by('lname').filter(active_status__exact='Active')
    staff_count = staffs.count()
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid(): 
            form.save()
            return HttpResponseRedirect('newstaff')
    else:
        form = EmployeeForm
        if 'submitted' in request.GET:
            submitted = True
    context = {
                'form':form,
               'submitted':submitted,
               'staffs':staffs,
               'staff_count':staff_count,
               'RBA':RBA,
               'STAFFLEVEL':STAFFLEVEL,
               'STAFFSTATUS':STAFFSTATUS,
               'STAFFRANK':STAFFRANK,
               'GENDER':GENDER,
               'DEPENDANTS':DEPENDANTS,
               'HEQ':HEQ,
               'REGION':REGION,
               'TITLE':TITLE,
               'SUFFIX':SUFFIX,
               
               }
    return render(request,'hr/new_staff.html',context)



def staff_education(request,staffno):
    # stno = request.POST['staffno']
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
    context = {'HEQ':HEQ,'form':form,'schools':schools,'staff':staff,'school_list':school_list,'submitted':submitted}
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
def dependants(request,staffno):
    submitted = False
    dependant_list = Kith.objects.order_by('kith_dob')
    staff = Employee.objects.get(pk=staffno)
    dependants = Kith.objects.order_by('kith_dob').filter(staffno__exact=staffno)
    if request.method == 'POST':
        form = KithForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('dependants', staffno)
    else:
        form = KithForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'dependants':dependants,'staff':staff,'dependant_list':dependant_list,'submitted':submitted,'GENDER':GENDER,'DEPENDANTS':DEPENDANTS}
    return render(request,'hr/dependants.html',context)

def edit_dependants(request,dep_id,staffno):
    dependant_list = Kith.objects.order_by('kith_dob')
    staff = Employee.objects.get(pk=staffno)
    dependants = Kith.objects.order_by('kith_dob').filter(staffno__exact=staffno)
    coy_count = dependants.count()
    dependant = Kith.objects.get(pk=dep_id)
    pkno = dependant.id
    form = KithForm(request.POST or None,instance=dependant)

    if request.method == 'POST':
        form = KithForm(request.POST, instance=dependant)
        if form.is_valid():
            form.save()
            return redirect('dependants', staffno)

    context = {'pkno':pkno,'form':form,'dependants':dependants,'coy_count':coy_count,'dependant':dependant,'staff':staff,'dependant_list':dependant_list,'GENDER':GENDER,'DEPENDANTS':DEPENDANTS}
    return render(request, 'hr/dependants.html', context)


def delete_dependants(request,dep_id,staffno):
    dependant = Kith.objects.get(pk=dep_id)
    # dependant = dependant.coy_name
    if request.method == 'POST':
       dependant.delete()
       return redirect('dependants', staffno)
    return render(request, 'delete.html',{'obj':dependant})

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
    context = {'current_rank':current_rank,'form':form,'promotions':promotions,'staff':staff,'jobtitle_list':jobtitle_list,'submitted':submitted,'STAFFRANK':STAFFRANK}
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
    context = {'form':form,'bereavement_list':bereavement_list,'submitted':submitted,'staff':staff,'DEPENDANTS':DEPENDANTS}
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
    context = {'form':form,'marriage_list':marriage_list,'submitted':submitted,'staff':staff,'DEPENDANTS':DEPENDANTS}
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