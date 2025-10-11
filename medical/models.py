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
        amount_used = Medical.objects.filter(staffno=staff, staff_cat=self.staff_cat, nature=self.treatment_type, academic_year=self.academic_year).aggregate(models.Sum('treatment_cost'))['treatment_cost__sum'] or Decimal('0.00')       
        return amount_used
    
    def get_remaining_amount(self, staff):
        used = self.get_amount_used(staff)
        remaining = self.entitlement - used
        return remaining if remaining > 0 else Decimal('0.00')
    
    # def get_surcharge(self, staff):
    #     amount_used = self.get_amount_used(staff)
    #     surcharge = amount_used - self.entitlement
    #     return surcharge if surcharge > 0 else Decimal('0.00')
    
    def get_actual_surcharge(self, staff):
        """Get surcharge amount considering payments"""
        amount_used = self.get_amount_used(staff)
        gross_surcharge = amount_used - self.entitlement if amount_used > self.entitlement else Decimal('0.00')
        
        if gross_surcharge > 0:
            # Check for existing surcharge records and their payments
            surcharges = MedicalSurcharge.objects.filter(
                staff=staff,
                academic_year=self.academic_year,
                medical_transaction__nature=self.treatment_type
            )
            total_paid = surcharges.aggregate(models.Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
            return gross_surcharge - total_paid
        return Decimal('0.00')
    
    def get_surcharge_details(self, staff):
        """Get detailed surcharge information"""
        amount_used = self.get_amount_used(staff)
        gross_surcharge = amount_used - self.entitlement if amount_used > self.entitlement else Decimal('0.00')
        
        surcharge_records = MedicalSurcharge.objects.filter(
            staffno=staff,
            academic_year=self.academic_year,
            medical_transaction__nature=self.treatment_type
        )
        
        total_paid = surcharge_records.aggregate(models.Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        total_balance = surcharge_records.aggregate(models.Sum('balance'))['balance__sum'] or Decimal('0.00')
        
        return {
            'gross_surcharge': gross_surcharge,
            'total_paid': total_paid,
            'balance': total_balance,
            'active_surcharges': surcharge_records.filter(status='active').count(),
            'monthly_deduction': surcharge_records.filter(status='active').aggregate(models.Sum('monthly_deduction'))['monthly_deduction__sum'] or Decimal('0.00')
        }