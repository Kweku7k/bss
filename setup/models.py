from django.db import models # type: ignore

from .choices import STAFFLEVEL

# Create your models here.
class School(models.Model):
    school_name = models.CharField('Name of School',max_length=150,blank=False,null=False)
    school_code = models.CharField('Short Name',max_length=50,blank=True,null=True)
    school_location = models.CharField('Short Location',max_length=200,blank=True,null=True)
    school_notes = models.TextField('Notes',blank=True,null=True)
    school_type = models.CharField(default='SS', max_length=120 ,choices=[('BS','Basic School'),('SS','Secondary School'),('TC','Post Secondary School'),('UN','University')])
    updated = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.school_name

class ProfBody(models.Model):
    assoc_long_name = models.CharField('Name of Association',max_length=250,blank=False,null=False)
    assoc_short_name = models.CharField('Short Name',max_length=50,blank=True,null=True)
    assoc_notes = models.TextField('Notes',blank=True,null=True)
    def __str__(self):
        return self.assoc_long_name

class Bank(models.Model):
    bank_short_name = models.CharField('Bank Short Name',max_length=250,blank=False,null=False)
    bank_notes = models.TextField('Notes',blank=True,null=True)
    export_format = models.JSONField('Export Format', blank=True, null=True)
    def __str__(self):
        return self.bank_short_name
    
class Title(models.Model):
    title_name = models.CharField('Title',max_length=250,blank=False,null=False)
    title_abbr = models.CharField('Abbreviation',max_length=50,blank=True,null=True)
    def __str__(self):
        return self.title_abbr
    
class Qualification(models.Model):
    qual_name = models.CharField('Qualification Title',max_length=250,blank=False,null=False)
    qual_abbr = models.CharField('Abbreviation',max_length=50,blank=True,null=True)
    def __str__(self):
        return self.qual_abbr
    
class StaffCategory(models.Model):
    category_name = models.CharField('Staff Category',max_length=250,blank=False,null=False)
    category_abbr = models.CharField('Abbreviation',max_length=50,blank=True,null=True)
    def __str__(self):
        return self.category_name
    
class Contract(models.Model):
    contract_type = models.CharField('Contract Type',max_length=250,blank=False,null=False)
    def __str__(self):
        return self.contract_type
    
class Campus(models.Model):
    campus_name = models.CharField('Campus',max_length=250,blank=False,null=False)
    def __str__(self):
        return self.campus_name
    
class Directorate(models.Model):
    direct_name = models.CharField('Directorate',max_length=250,blank=False,null=False)
    def __str__(self):
        return self.direct_name
    
    
class School_Faculty(models.Model):
    sch_fac_name = models.CharField('School/Faculty',max_length=250,blank=False,null=False)
    def __str__(self):
        return self.sch_fac_name
    
class Department(models.Model):
    dept_long_name = models.CharField('Name of Department',max_length=250,blank=False,null=False)
    dept_short_name = models.CharField('Short Name',max_length=50,blank=True,null=True)
    sch_fac = models.ForeignKey(School_Faculty, on_delete=models.CASCADE, blank=True, null=True)
    dept_notes = models.TextField('Notes',blank=True,null=True)
    def __str__(self):
        return self.dept_long_name
    
    
class Unit(models.Model):
    unit_name = models.CharField('Name of Unit', max_length=250, blank=False, null=False)
    unit_short_name = models.CharField('Short Name', max_length=50, blank=True, null=True)
    directorate = models.ForeignKey(Directorate, on_delete=models.CASCADE, blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return self.unit_name


class BankBranch(models.Model):
    branch_name = models.CharField('Name of Branch',max_length=250,blank=False,null=False)
    bank_code = models.ForeignKey(Bank,on_delete=models.CASCADE,blank=True,null=True)
    branch_location = models.TextField('Branch Location',max_length=300,blank=False,null=False)
    sort_code = models.CharField('Sort Code', max_length=50, blank=True, null=True)
    def __str__(self):
        return self.branch_name

class Hospital(models.Model):
    hospital_name = models.CharField('Name of Hospital',max_length=250,blank=False,null=False)
    hospital_location = models.CharField('Location of Hospital',max_length=250,blank=False,null=False)
    hospital_contact_name = models.CharField('Name of Contact',max_length=250,blank=True,null=True)
    hospital_contact_phone = models.CharField('Contact Phone',max_length=25,blank=True,null=True)
    def __str__(self):
        return self.hospital_name
    
class StaffRank(models.Model):
    staff_rank = models.CharField("Staff Rank",max_length=150,blank=False,null=False)
    staff_level = models.CharField("Staff Level",max_length=50,blank=False,null=False,choices=STAFFLEVEL)
    rank_notes = models.TextField("Notes",blank=True,null=True)

class JobTitle(models.Model):
    job_title = models.CharField("Job Title",max_length=150,blank=False,null=False)
    staff_cat = models.CharField('Staff Category',max_length=100,blank=True,null=True)
    salary_level = models.CharField("Salary Level",max_length=150,blank=True,null=True)
    jobtitle_notes = models.TextField("Notes",blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True) 
    
    def __str__(self):
        return self.job_title


class AcademicYear(models.Model):
    academic_year = models.CharField(max_length=10)
    active = models.BooleanField(default=False)
    
    def __str__(self):
        return self.academic_year
    
    def save(self, *args, **kwargs):
        if self.active:
            # Deactivate other academic years
            AcademicYear.objects.exclude(pk=self.pk).update(active=False)
        super().save(*args, **kwargs)
    
    
    
class IncomeType(models.Model):
    name = models.CharField(max_length=100, blank=False,null=False)
    taxable = models.BooleanField(default=False)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, blank=True, null=True)
    bik_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, blank=True, null=True)
    bik_cap = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True, null=True)

    def __str__(self):
        return self.name
    
class DeductionType(models.Model):
    name = models.CharField(max_length=100, blank=False,null=False)

    def __str__(self):
        return self.name

class SalaryScale(models.Model):
    name = models.CharField(max_length=100, blank=False,null=False)
    def __str__(self):
        return self.name
    
    
class ContributionRate(models.Model):
    employee_ssnit_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, blank=True, null=True)
    employer_ssnit_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, blank=True, null=True)
    employee_pf_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, blank=True, null=True)
    employer_pf_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, blank=True, null=True)
    withholding_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.created.strftime("%Y-%m-%d")
    
    
class TaxBand(models.Model):
    lower_limit = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    upper_limit = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="e.g. 17.5% = 0.175")

    def __str__(self):
        return f"{self.lower_limit} - {self.upper_limit} @ {self.rate * 100:.1f}%"
