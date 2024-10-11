from django.db import models 
from hr.models import *
from setup.models import *

class Leave(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE) # Link to Employees model
    leave_entitlement = models.IntegerField()
    staff_rank  = models.CharField(max_length=25,blank=False,null=False)
    fin_year = models.CharField(max_length=10,blank=False,null=False,default='2025/26')
    leave_description = models.CharField(max_length=250,blank=False,null=False)
    leave_approved_by = models.CharField(max_length=250,blank=True,null=True,default='0000') 
    days_taken = models.IntegerField()
    leave_arrears = models.IntegerField()
    leave_approved_on = models.DateField(blank=True,null=True)
    remarks = models.CharField(max_length=250,blank=True,null=True)
    leave_start_date = models.DateField(blank=True,null=True)
    leave_end_date = models.DateField(blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    
class AcademicYear(models.Model):
    academic_year = models.CharField(max_length=20)
    
    def __str__(self):
        return self.academic_year
    
class LeaveEntitlement(models.Model):
    staff_cat = models.ForeignKey(StaffCategory, on_delete=models.SET_NULL, blank=True, null=True)
    entitlement = models.IntegerField()
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, blank=True, null=True)
        
    def get_remaining_days(self, staff):
        # Sum the days taken by this staff member
        total_days_taken = Staff_Leave.objects.filter(staffno=staff, staff_cat=self.staff_cat).aggregate(models.Sum('days_taken'))['days_taken__sum'] or 0
        remaining_days = self.entitlement - total_days_taken
        return remaining_days
    