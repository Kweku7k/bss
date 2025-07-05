from django.db import models
from hr.models import *
from setup.models import *
from leave.models import *

# Create your models here.

class MedicalEntitlement(models.Model):
    staff_cat = models.CharField('Staff Category',max_length=100, blank=True, null=True)
    treatment_type = models.CharField('Treatment Type', max_length=100, blank=True, null=True)
    entitlement = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True, null=True)
    academic_year = models.CharField(max_length=10, blank=True, null=True)

        
    def get_amount_used(self, staff):
        amount_used = Medical.objects.filter(staffno=staff, staff_cat=self.staff_cat, nature=self.treatment_type, academic_year=self.academic_year).aggregate(models.Sum('treatment_cost'))['treatment_cost__sum'] or 0        
        return amount_used
    
    def get_remaining_amount(self, staff):
        used = self.get_amount_used(staff)
        remaining = self.entitlement - used
        return remaining if remaining > 0 else Decimal('0.00')
    
    def get_surcharge(self, staff):
        amount_used = self.get_amount_used(staff)
        surcharge = amount_used - self.entitlement
        return surcharge if surcharge > 0 else Decimal('0.00')