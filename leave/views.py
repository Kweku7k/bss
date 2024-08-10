from datetime import date
from django.shortcuts import render # type: ignore
from .models import Leave
from hr.choices import STAFFRANK
from hr.models import ChoicesStaffRank, Employee
from .forms import *

# Create your views here.
def leave_entitlement(request):
    staffRank = ''
    num_days = 0
    fisc_yr = ''
    add_arrears = ''
    employees = ''
    leaves = ''
    all_leave_arrears = ''
    staff_leave_arrears = 0
    new_num_days = 0
    staff_no = ''
    msg = ''
    
    if request.method == 'POST':
        staffRank = request.POST['staff_rank']
        num_days = request.POST['leave_entitlement']
        fisc_yr = request.POST['fin_year']
        add_arrears = request.POST['add_arrears']

        # staff = Employee.objects.get(pk=staffno)
        
        employees = Employee.objects.order_by('lname').filter(active_status__exact='Active',staff_rank__exact=staffRank) 
        if employees is not None:
            for staff in employees:
                arrs = Leave.objects.values_list('leave_arrears').order_by('-id').filter(staffno_id__exact=staff.staffno)[0:1]
                # mydata = Member.objects.values_list('firstname')
                if arrs is not None:
                    if arrs:       #arrs.values()[0]['leave_arrears']:
                        qwe = arrs.values()[0]['leave_arrears']
                    else:
                        qwe = 0
                    # item_id_one = items.values()[0]["id"]
                    if add_arrears == 'YES':
                        new_num_days = int(num_days) +  qwe  #()[0:1]   #int(staff_leave_arrears)
                    else:
                        new_num_days = int(num_days)
                #     msg = "NO LEAVE arrears"
                form_data = {
                    "staffno":staff.staffno,
                    "leave_entitlement":num_days,
                    "staff_rank":[{q.name:q.name} for q in ChoicesStaffRank.query.all()],
                    "fin_year":fisc_yr,
                    "leave_description":"Annual Leave Entitlement",
                    "leave_approved_by":staff.staffno,
                    "days_taken":0,
                    "leave_arrears":new_num_days,
                    "leave_approved_on":"2024-10-10",
                    "remarks":"Annual Leave Entitlement",
                    "leave_start_date":"2024-10-10",
                    "leave_end_date":"2024-10-10",}
                f_data = LeaveForm(form_data) 
                if f_data.is_valid():
                    f_data.save()
            leaves = Leave.objects.filter(fin_year__exact=fisc_yr,staff_rank__exact=staffRank) 
            leaves = leaves.order_by('staffno')
                    
        context = {'name':'JASKAMWAY','STAFFRANK':[(q.name,q.name) for q in ChoicesStaffRank.objects.all()],'staff':staffRank, 'num_days':num_days,'yr':fisc_yr,'arr':add_arrears,
                   'employee':employees,
                   'leaves':leaves,
                   'msg':msg,
                   'all_leave_arrears':employees,
                #    'arrears':qwe
                   }
        return render(request,'leave/leave_entitlement.html',context)
    return render(request,'leave/leave_entitlement.html',{'STAFFRANK':[(q.name,q.name) for q in ChoicesStaffRank.objects.all()]})



############ LEAVE RWQUEST ##################

def leave_request(request):
    
    context = {}
    return render(request, 'leave/leave_request.html', context)
    