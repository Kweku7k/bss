from django.db import models # type: ignore
from hr.models import Employee

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

