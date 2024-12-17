from django.http import HttpResponseRedirect # type: ignore
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse # type: ignore
from .forms import *
from .choices import STAFFLEVEL
from setup.models import *
from django.http import JsonResponse
from django.contrib import messages
from django.forms import modelform_factory




# Create your views here.
def home(request):
    pass

########### SCHOOL VIEWS ################
def add_school(request):
    submitted = False
    schools = School_Faculty.objects.order_by('-id') 
    sch_count = schools.count() 
    if request.method == 'POST':
        form = School_FacultyForm(request.POST)
        if form.is_valid():
            # Check if the school already exists
            school_name = form.cleaned_data.get('sch_fac_name')
            if School_Faculty.objects.filter(sch_fac_name=school_name).exists():
                messages.error(request, f'{school_name} School already exists.')
                return redirect('add-school')
            else:
                form.save()
                return HttpResponseRedirect('school?submitted=True')
    else:
        form = School_FacultyForm
        if 'submitted' in request.GET:
            submitted = True
    context = {'form':form,'submitted':submitted,'schools':schools,'sch_count':sch_count}
    return render(request,'setup/add_schoolfaculty.html',context)


def delete_sch(request,sch_id):
    school = School_Faculty.objects.get(pk=sch_id)
    if request.method == 'GET':
       school.delete()
    return redirect('add-school')

def edit_school(request, sch_id):
    schools = School_Faculty.objects.order_by('-id') 
    sch_count = schools.count()
    school = School_Faculty.objects.get(pk=sch_id)
    form = School_FacultyForm(instance=school)

    if request.method == 'POST':
        form = School_FacultyForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            return redirect('add-school')

    context = {'form':form,'schools':schools,'sch_count':sch_count,'school':school}
    return render(request, 'setup/add_schoolfaculty.html', context)
########### END OF SCHOOL VIEWS ################


########### TITLE ################
def add_title(request):
    submitted = False
    titles = Title.objects.order_by('-id') 
    title_count = titles.count()
    if request.method == 'POST':
        form = TitleForm(request.POST)
        if form.is_valid(): 
            # Check if the title already exists
            title_name = form.cleaned_data.get('title_name')
            if Title.objects.filter(title_name=title_name).exists():
                messages.error(request, f'{title_name} Title already exists.')
                return redirect('add-title')
            else:
                form.save()
                return HttpResponseRedirect('title?submitted=True')
    else:
        form = TitleForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_title.html',{'form':form,'submitted':submitted,'titles':titles,'title_count':title_count})

def delete_title(request,title_id):
    title = Title.objects.get(pk=title_id)
    if request.method == 'GET':
       title.delete()
    return redirect('add-title')

def edit_title(request, title_id):
    titles = Title.objects.order_by('-id') 
    title_count = titles.count()
    title = Title.objects.get(pk=title_id)
    form = TitleForm(instance=title)

    if request.method == 'POST':
        form = TitleForm(request.POST, instance=title)
        if form.is_valid():
            form.save()
            return redirect('add-title')

    context = {'form':form,'titles':titles,'title_count':title_count,'title':title}
    return render(request, 'setup/add_title.html', context)
########### END OF TITLE ################

########### QUALIFICATIONS ################
def add_qualification(request):
    submitted = False
    quals = Qualification.objects.order_by('-id') 
    qual_count = quals.count()
    if request.method == 'POST':
        form = QualificationForm(request.POST)
        if form.is_valid(): 
            # Check if the qualification already exists
            qual_name = form.cleaned_data.get('qual_name')
            if Qualification.objects.filter(qual_name=qual_name).exists():
                messages.error(request, f'{qual_name} Qualification already exists.')
                return redirect('add-qualification')
            else:
                form.save()
                return HttpResponseRedirect('qualification?submitted=True')
    else:
        form = QualificationForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_qualification.html',{'form':form,'submitted':submitted,'quals':quals,'qual_count':qual_count})

def delete_qualification(request,qual_id):
    qual = Qualification.objects.get(pk=qual_id)
    if request.method == 'GET':
       qual.delete()
    return redirect('add-qualification')

def edit_qualification(request, qual_id):
    quals = Qualification.objects.order_by('-id') 
    qual_count = quals.count()
    qual = Qualification.objects.get(pk=qual_id)
    form = QualificationForm(instance=qual)

    if request.method == 'POST':
        form = QualificationForm(request.POST, instance=qual)
        if form.is_valid():
            form.save()
            return redirect('add-qualification')

    context = {'form':form,'quals':quals,'qual_count':qual_count,'qual':qual}
    return render(request, 'setup/add_qualification.html', context)
########### END OF QUALIFICATIONS ################

########### STAFF CATEGORY ################
def add_staffcategory(request):
    submitted = False
    staffcategorys = StaffCategory.objects.order_by('-id') 
    staffcategory_count = staffcategorys.count()
    if request.method == 'POST':
        form = StaffCategoryForm(request.POST)
        if form.is_valid(): 
            category_name = form.cleaned_data.get('category_name')
            if StaffCategory.objects.filter(category_name=category_name).exists():
                messages.error(request, f'{category_name} Staff Category already exists.')
                return redirect('add-staffcategory')
            else:
                form.save()
                return HttpResponseRedirect('staffcategory?submitted=True')
    else:
        form = StaffCategoryForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_staffcategory.html',{'form':form,'submitted':submitted,'staffcategorys':staffcategorys,'staffcategory_count':staffcategory_count})

def delete_staffcategory(request,sc_id):
    staffcategory = StaffCategory.objects.get(pk=sc_id)
    if request.method == 'GET':
       staffcategory.delete()
    return redirect('add-staffcategory')

def edit_staffcategory(request, sc_id):
    staffcategorys = StaffCategory.objects.order_by('-id') 
    staffcategory_count = staffcategorys.count()
    staffcategory = StaffCategory.objects.get(pk=sc_id)
    form = StaffCategoryForm(instance=staffcategory)

    if request.method == 'POST':
        form = StaffCategoryForm(request.POST, instance=staffcategory)
        if form.is_valid():
            form.save()
            return redirect('add-staffcategory')

    context = {'form':form,'staffcategorys':staffcategorys,'staffcategory_count':staffcategory_count,'staffcategory':staffcategory}
    return render(request, 'setup/add_staffcategory.html', context)
########### END OF STAFF CATEGORY ################

########### CONTRACT ################
def add_contract(request):
    submitted = False
    contracts = Contract.objects.order_by('-id') 
    contract_count = contracts.count()
    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid(): 
            # Check if the contract already exists
            contract_type = form.cleaned_data.get('contract_type')
            if Contract.objects.filter(contract_type__iexact=contract_type).exists():

                messages.error(request, f'{contract_type} Contract Type already exists.')
                return redirect('add-contract')
            else:
                form.save()
                return HttpResponseRedirect(reverse('add-contract') + '?submitted=True')
    else:
        form = ContractForm()
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_contract.html',{'form':form,'submitted':submitted,'contracts':contracts,'contract_count':contract_count})

def delete_contract(request,ct_id):
    contract = get_object_or_404(Contract, pk=ct_id)
    if request.method == 'GET':
        contract.delete()
        messages.success(request, 'Contract deleted successfully.')
    return redirect('add-contract')


def edit_contract(request, ct_id):
    contracts = Contract.objects.order_by('-id')
    contract_count = contracts.count()
    contract = get_object_or_404(Contract, pk=ct_id)
    form = ContractForm(instance=contract)

    if request.method == 'POST':
        form = ContractForm(request.POST, instance=contract)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contract updated successfully.')
            return redirect('add-contract')

    context = {
        'form': form,
        'contracts': contracts,
        'contract_count': contract_count,
        'contract': contract,
    }
    return render(request, 'setup/add_contract.html', context)

########### CONTRACT ################

########### CAMPUS VIEW ################
def add_campus(request):
    submitted = False
    campus = Campus.objects.order_by('-id')
    campus_count = campus.count()
    if request.method == 'POST':
        form = CampusForm(request.POST)
        if form.is_valid():
            # Check if the campus already exists
            campus_name = form.cleaned_data.get('campus_name')
            if Campus.objects.filter(campus_name=campus_name).exists():
                messages.error(request, f'{campus_name} Campus already exists.')
                return redirect('add-campus')
            else:
                form.save()
                return HttpResponseRedirect('campus?submitted=True')
    else:
        form = CampusForm
        if 'submitted' in request.GET:
            submitted = True
                
    return render(request,'setup/add_campus.html',{'form':form,'submitted':submitted,'campus':campus,'campus_count':campus_count })


def delete_campus(request,camp_id):
    campus = Campus.objects.get(pk=camp_id)
    if request.method == 'GET':
       campus.delete()
    return redirect('add-campus')

def edit_campus(request, camp_id):
    campus = Campus.objects.order_by('-id') 
    campus_count = campus.count()
    camp = Campus.objects.get(pk=camp_id)
    form = CampusForm(instance=camp)

    if request.method == 'POST':
        form = CampusForm(request.POST, instance=camp)
        if form.is_valid():
            form.save()
            return redirect('add-campus')

    context = {'form':form,'campus':campus,'campus_count':campus_count,'camp':camp}
    return render(request, 'setup/add_campus.html', context)
        
########### END OF CAMPUS VIEW ################

########### DIRECTORATE VIEW ################
def add_directorate(request):
    submitted = False
    directorate = Directorate.objects.order_by('-id')
    dict_count = directorate.count()
    if request.method == 'POST':
        form = DirectorateForm(request.POST)
        if form.is_valid():
            # Check if the directorate already exists
            direct_name = form.cleaned_data.get('direct_name')
            if Directorate.objects.filter(direct_name=direct_name).exists():
                messages.error(request, f'{direct_name} Directorate already exists.')
                return redirect('add-directorate')
            else:
                form.save()
                return HttpResponseRedirect('directorate?submitted=True')
    else:
        form = DirectorateForm
        if 'submitted' in request.GET:
            submitted = True
                
    return render(request,'setup/add_directorate.html',{'form':form,'submitted':submitted,'directorate':directorate,'dict_count':dict_count })

def delete_directorate(request,dict_id):
    directorate = Directorate.objects.get(pk=dict_id)
    if request.method == 'GET':
       directorate.delete()
    return redirect('add-directorate')

def edit_directorate(request, dict_id):
    directorate = Directorate.objects.order_by('-id') 
    dict_count = directorate.count()
    dict = Directorate.objects.get(pk=dict_id)
    form = DirectorateForm(instance=dict)

    if request.method == 'POST':
        form = DirectorateForm(request.POST, instance=dict)
        if form.is_valid():
            form.save()
            return redirect('add-directorate')

    context = {'form':form,'directorate':directorate,'dict_count':dict_count,'dict':dict}
    return render(request, 'setup/add_directorate.html', context)
        
########### END OF DIRECTORATE VIEW ################

########### PROFESSIONAL BODIES VIEWS ################
def add_profbody(request):
    submitted = False
    profbodys = ProfBody.objects.order_by('-id') 
    pb_count = profbodys.count()
    if request.method == 'POST':
        form = ProfBodyForm(request.POST)
        if form.is_valid(): 
            # Check if the professional body already exists
            assoc_long_name = form.cleaned_data.get('assoc_long_name')
            if ProfBody.objects.filter(assoc_long_name=assoc_long_name).exists():
                messages.error(request, f'{assoc_long_name} Professional Body already exists.')
                return redirect('add-profbody')
            else:
                form.save()
                return HttpResponseRedirect('profbody?submitted=True')
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
    schools = School_Faculty.objects.all()
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid(): 
            # Check if the department already exists
            dept_long_name = form.cleaned_data.get('dept_long_name')
            sch_fac = form.cleaned_data.get('sch_fac')
            if Department.objects.filter(dept_long_name=dept_long_name, sch_fac=sch_fac).exists():
                messages.error(request, f'{dept_long_name} Department already exists  for {sch_fac}.')
                return redirect('add-dept')
            else:
                form.save()
                return HttpResponseRedirect('dept?submitted=True')
    else:
        form = DepartmentForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_dept.html',{'form':form,'submitted':submitted,'depts':depts,'dept_count':dept_count, 'schools':schools})

def delete_dept(request,dept_id):
    dept = Department.objects.get(pk=dept_id)
    if request.method == 'GET':
       dept.delete()
    return redirect('add-dept')

def edit_dept(request, dept_id):
    depts = Department.objects.order_by('-id') 
    dept_count = depts.count()
    schools = School_Faculty.objects.all()
    dept = Department.objects.get(pk=dept_id)
    form = DepartmentForm(instance=dept)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            return redirect('add-dept')

    context = {'form':form,'depts':depts,'dept_count':dept_count,'dept':dept, 'schools':schools}
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
            # Check if the hospital already exists
            hospital_name = form.cleaned_data.get('hospital_name')
            if Hospital.objects.filter(hospital_name=hospital_name).exists():
                messages.error(request, f'{hospital_name} Hospital already exists.')
                return redirect('add-hosp')
            else:
                form.save()
                return HttpResponseRedirect('hosp?submitted=True')
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
            # Check if the bank already exists
            bank_long_name = form.cleaned_data.get('bank_long_name')
            if Bank.objects.filter(bank_long_name=bank_long_name).exists():
                messages.error(request, f'{bank_long_name} Bank already exists.')
                return redirect('add-bank')
            else:
                form.save()
                return HttpResponseRedirect('bank?submitted=True')
    else:
        form = BankForm
        if 'submitted' in request.GET:
            submitted = True

    context = {'form':form,'submitted':submitted,'banks':banks,'bank_count':bank_count}
    return render(request,'setup/add_bank.html',context)

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
            # Check if the bank branch already exists
            branch_name = form.cleaned_data.get('branch_name')
            bank_code = form.cleaned_data.get('bank_code')
            
            if BankBranch.objects.filter(branch_name=branch_name, bank_code=bank_code).exists():
                messages.error(request, f'{branch_name} Branch already exists for {bank_code} Bank.')
                return redirect('add-bankbranch')
            else:            
                form.save()
                return HttpResponseRedirect('bankbranch?submitted=True')
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

########### END OF BANK BRANCH VIEWS ################

########### STAFF RANK VIEWS ################
def add_jobtitle(request):
    submitted = False
    staffcategorys = StaffCategory.objects.order_by('category_abbr') 
    jobtitles = JobTitle.objects.order_by('-id') 
    jobtitle_count = jobtitles.count()
    if request.method == 'POST':
        form = JobTitleForm(request.POST)
        print(form)
        if form.is_valid(): 
            form.save()
            print("Form validated successfully")
            print("Form validated successfully")
            return HttpResponseRedirect('jobtitle')
            # return redirect('add-jobtitle')
    else:
        form = JobTitleForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request,'setup/add_jobtitle.html',{'form':form,'submitted':submitted,'jobtitles':jobtitles,'jobtitle_count':jobtitle_count,'staffcategorys':staffcategorys})

def delete_jobtitle(request,jobtitle_id):
    jobtitle = JobTitle.objects.get(pk=jobtitle_id)
    if request.method == 'GET':
       jobtitle.delete()
    return redirect('add-jobtitle')

def edit_jobtitle(request, jobtitle_id):
    jobtitles = JobTitle.objects.order_by('-id') 
    jobtitle_count = jobtitles.count()
    staffcategorys = StaffCategory.objects.order_by('category_abbr') 
    jobtitle = JobTitle.objects.get(pk=jobtitle_id)
    form = JobTitleForm(instance=jobtitle)

    if request.method == 'POST':
        form = JobTitleForm(request.POST, instance=jobtitle)
        if form.is_valid():
            form.save()
            return redirect('add-jobtitle')

    context = {'form':form,'jobtitles':jobtitles,'jobtitle_count':jobtitle_count,'jobtitle':jobtitle,'STAFFLEVEL':STAFFLEVEL, 'staffcategorys':staffcategorys}
    return render(request, 'setup/add_jobtitle.html', context)
########### END OF STAFF RANK VIEWS ################

########### DYNAMIC CHOICE VIEWS ################

def generic_model_crud(request, model_class, model_name, template_name):
    # Generic function to handle Add, Edit, and Delete for models with a 'name' field.
    
    form_class = modelform_factory(model_class, fields=['name'])  # Dynamically create the form
    records = model_class.objects.order_by('-id')  # Fetch all records
    record_count = records.count()  # Count total records

    record = None
    if 'edit_id' in request.GET:
        record = get_object_or_404(model_class, id=request.GET['edit_id'])  # Edit record

    if request.method == 'POST':
        if 'delete_id' in request.POST:  # Handle Delete
            delete_record = get_object_or_404(model_class, id=request.POST['delete_id'])
            delete_record.delete()
            messages.success(request, f"{model_name} has been deleted successfully.")
            return redirect(request.path)

        form = form_class(request.POST, instance=record)  # Add/Edit Form
        if form.is_valid():
            name = form.cleaned_data['name']
            if not record and model_class.objects.filter(name=name).exists():
                messages.error(request, f"{model_name} '{name}' already exists.")
            else:
                form.save()
                if record:
                    messages.success(request, f"{model_name} has been updated successfully.")
                else:
                    messages.success(request, f"New {model_name} has been added successfully.")
                return redirect(request.path)
    else:
        form = form_class(instance=record)

    context = {
        'form': form,
        'records': records,
        'record_count': record_count,
        'model_name': model_name,
        'record': record,
    }
    return render(request, template_name, context)