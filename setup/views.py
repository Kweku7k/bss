from django.http import HttpResponseRedirect # type: ignore
from django.shortcuts import redirect, render # type: ignore
from .forms import *
from .choices import STAFFLEVEL
from setup.models import *

# Create your views here.
def home(request):
    pass

########### SCHOOL VIEWS ################
def add_school(request):
    submitted = False
    schools = School.objects.order_by('-id') 
    sch_count = schools.count()
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        if form.is_valid(): 
            print("---form----")

            form.save()
            return HttpResponseRedirect('school')
    else:
        form = SchoolForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'submitted':submitted,'schools':schools,'sch_count':sch_count}
    return render(request,'setup/add_school.html',context)


def delete_sch(request,sch_id):
    school = School.objects.get(pk=sch_id)
    if request.method == 'GET':
       school.delete()
    return redirect('add-school')

def edit_school(request, sch_id):
    schools = School.objects.order_by('-id') 
    sch_count = schools.count()
    school = School.objects.get(pk=sch_id)
    form = SchoolForm(instance=school)

    if request.method == 'POST':
        form = SchoolForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            return redirect('add-school')

    context = {'form':form,'schools':schools,'sch_count':sch_count,'school':school}
    return render(request, 'setup/add_school.html', context)
########### END OF SCHOOL VIEWS ################

########### PROFESSIONAL BODIES VIEWS ################
def add_profbody(request):
    submitted = False
    profbodys = ProfBody.objects.order_by('-id') 
    pb_count = profbodys.count()
    if request.method == 'POST':
        form = ProfBodyForm(request.POST)
        if form.is_valid(): 
            form.save()
            return HttpResponseRedirect('profbody')
    else:
        form = ProfBodyForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_profbody.html',{'form':form,'submitted':submitted,'profbodys':profbodys,'pb_count':pb_count})

def delete_profbody(request,pb_id):
    profbody = ProfBody.objects.get(pk=pb_id)
    if request.method == 'GET':
       profbody.delete()
    return redirect('add-profbody')

def edit_profbody(request, pb_id):
    profbodys = ProfBody.objects.order_by('-id') 
    pb_count = profbodys.count()
    profbody = ProfBody.objects.get(pk=pb_id)
    form = ProfBodyForm(instance=profbody)

    if request.method == 'POST':
        form = ProfBodyForm(request.POST, instance=profbody)
        if form.is_valid():
            form.save()
            return redirect('add-profbody')

    context = {'form':form,'profbodys':profbodys,'pb_count':pb_count,'profbody':profbody}
    return render(request, 'setup/add_profbody.html', context)
########### END OF PROFESSIONAL BODIES VIEWS ################

########### DEPARTMENT VIEWS ################
def add_dept(request):
    submitted = False
    depts = Department.objects.order_by('-id') 
    dept_count = depts.count()
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid(): 
            form.save()
            return HttpResponseRedirect('dept')
    else:
        form = DepartmentForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_dept.html',{'form':form,'submitted':submitted,'depts':depts,'dept_count':dept_count})

def delete_dept(request,dept_id):
    dept = Department.objects.get(pk=dept_id)
    if request.method == 'GET':
       dept.delete()
    return redirect('add-dept')

def edit_dept(request, dept_id):
    depts = Department.objects.order_by('-id') 
    dept_count = depts.count()
    dept = Department.objects.get(pk=dept_id)
    form = DepartmentForm(instance=dept)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            return redirect('add-dept')

    context = {'form':form,'depts':depts,'dept_count':dept_count,'dept':dept}
    return render(request, 'setup/add_dept.html', context)
########### END OF DEPARTMENT VIEWS ################

########### HOSPITAL VIEWS ################
def add_hosp(request):
    submitted = False
    hosps = Hospital.objects.order_by('-id') 
    hosp_count = hosps.count()
    if request.method == 'POST':
        form = HospitalForm(request.POST)
        if form.is_valid(): 
            form.save()
            return HttpResponseRedirect('hosp')
    else:
        form = HospitalForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_hosp.html',{'form':form,'submitted':submitted,'hosps':hosps,'hosp_count':hosp_count})

def delete_hosp(request,hosp_id):
    hosp = Hospital.objects.get(pk=hosp_id)
    if request.method == 'GET':
       hosp.delete()
    return redirect('add-hosp')

def edit_hosp(request, hosp_id):
    hosps = Hospital.objects.order_by('-id') 
    hosp_count = hosps.count()
    hosp = Hospital.objects.get(pk=hosp_id)
    form = HospitalForm(instance=hosp)

    if request.method == 'POST':
        form = HospitalForm(request.POST, instance=hosp)
        if form.is_valid():
            form.save()
            return redirect('add-hosp')

    context = {'form':form,'hosps':hosps,'hosp_count':hosp_count,'hosp':hosp}
    return render(request, 'setup/add_hosp.html', context)
########### END OF HOSPITAL VIEWS ################

########### BANK VIEWS ################
def add_bank(request):
    submitted = False
    banks = Bank.objects.order_by('-id') 
    bank_count = banks.count()
    if request.method == 'POST':
        form = BankForm(request.POST)
        if form.is_valid(): 
            form.save()
            return HttpResponseRedirect('bank')
    else:
        form = BankForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_bank.html',{'form':form,'submitted':submitted,'banks':banks,'bank_count':bank_count})

def delete_bank(request,bank_id):
    bank = Bank.objects.get(pk=bank_id)
    if request.method == 'GET':
       bank.delete()
    return redirect('add-bank')

def edit_bank(request, bank_id):
    banks = Bank.objects.order_by('-id') 
    bank_count = banks.count()
    bank = Bank.objects.get(pk=bank_id)
    form = BankForm(instance=bank)

    if request.method == 'POST':
        form = BankForm(request.POST, instance=bank)
        if form.is_valid():
            form.save()
            return redirect('add-bank')

    context = {'form':form,'banks':banks,'bank_count':bank_count,'bank':bank}
    return render(request, 'setup/add_bank.html', context)
########### END OF BANK VIEWS ################

########### BANK BRANCH VIEWS ################
def add_bankbranch(request):
    submitted = False
    banks = Bank.objects.order_by('bank_long_name')
    bankbranchs = BankBranch.objects.order_by('-id') 
    bankbranch_count = bankbranchs.count()
    if request.method == 'POST':
        form = BankBranchForm(request.POST)
        if form.is_valid(): 
            form.save()
            return HttpResponseRedirect('bankbranch')
    else:
        form = BankBranchForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_bankbranch.html',{'form':form,'submitted':submitted,'bankbranchs':bankbranchs,'bankbranch_count':bankbranch_count,'banks':banks})

def delete_bankbranch(request,bankbranch_id):
    bankbranch = BankBranch.objects.get(pk=bankbranch_id)
    if request.method == 'GET':
       bankbranch.delete()
    return redirect('add-bankbranch')

def edit_bankbranch(request, bankbranch_id,bankid):
    banks = Bank.objects.order_by('bank_long_name')
    bankbranchs = BankBranch.objects.order_by('-id') 
    #bankbranchs = bankbranchs.filter(pk__exact=bankbranch_id)
    bankbranchs = bankbranchs.filter(bank_code_id__exact=bankid)
    bankbranch_count = bankbranchs.count()
    bankbranch = BankBranch.objects.get(pk=bankbranch_id)
    #bank_pk = bankid
    form = BankBranchForm(instance=bankbranch)

    if request.method == 'POST':
        form = BankBranchForm(request.POST, instance=bankbranch)
        if form.is_valid():
            form.save()
            return redirect('add-bankbranch')

    context = {
                'form':form,
               'bankbranchs':bankbranchs,
               'bankbranch_count':bankbranch_count,
               'bankbranch':bankbranch,
               'banks':banks,
            #    'bank_pk':bank_pk
               }
    return render(request, 'setup/add_bankbranch.html', context)
########### END OF BANK VIEWS staffrank ################

########### STAFF RANK VIEWS ################
def add_jobtitle(request):
    submitted = False
    jobtitles = JobTitle.objects.order_by('-id') 
    jobtitle_count = jobtitles.count()
    if request.method == 'POST':
        form = JobTitleForm(request.POST)
        if form.is_valid(): 
            form.save()
            # return HttpResponseRedirect('add-jobtitle')
            return redirect('add-jobtitle')
    else:
        form = JobTitleForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_jobtitle.html',{'form':form,'submitted':submitted,'jobtitles':jobtitles,'jobtitle_count':jobtitle_count,'STAFFLEVEL':STAFFLEVEL})

def delete_jobtitle(request,jobtitle_id):
    jobtitle = JobTitle.objects.get(pk=jobtitle_id)
    if request.method == 'POST':
       jobtitle.delete()
       return redirect('add-jobtitle')
    return render(request, 'delete.html',{'obj':jobtitle.job_title})

# def delete_vehicle(request,veh_id,staffno):
#     vehicle = Vehicle.objects.get(pk=veh_id)
#     # vehicle = vehicle.coy_name
#     if request.method == 'POST':
#        vehicle.delete()
#        return redirect('vehicle', staffno)
#     return render(request, 'delete.html',{'obj':vehicle.car_no})



def edit_jobtitle(request, jobtitle_id):
    jobtitles = JobTitle.objects.order_by('-id') 
    jobtitle_count = jobtitles.count()
    jobtitle = JobTitle.objects.get(pk=jobtitle_id)
    form = JobTitleForm(instance=jobtitle)

    if request.method == 'POST':
        form = JobTitleForm(request.POST, instance=jobtitle)
        if form.is_valid():
            form.save()
            return redirect('add-jobtitle')

    context = {'form':form,'jobtitles':jobtitles,'jobtitle_count':jobtitle_count,'jobtitle':jobtitle,'STAFFLEVEL':STAFFLEVEL}
    return render(request, 'setup/add_jobtitle.html', context)
########### END OF STAFF RANK VIEWS ################