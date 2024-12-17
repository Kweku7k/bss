from django.db import models
from hr.models import *
from setup.models import *
from leave.models import *

# Create your models here.

class MedicalEntitlement(models.Model):
    staff_cat = models.ForeignKey(StaffCategory, on_delete=models.SET_NULL, blank=True, null=True)
    entitlement = models.IntegerField()
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, blank=True, null=True)
        
    def get_remaining_amount(self, staff):
        # Sum the days taken by this staff member
        amount_used = Medical.objects.filter(staffno=staff, staff_cat=self.staff_cat).aggregate(models.Sum('treatment_cost'))['treatment_cost__sum'] or 0
        remaining_amount = self.entitlement - amount_used
        return remaining_amount
