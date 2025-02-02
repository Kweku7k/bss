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

class Department(models.Model):
    dept_long_name = models.CharField('Name of Department',max_length=250,blank=False,null=False)
    dept_short_name = models.CharField('Short Name',max_length=50,blank=True,null=True)
    dept_notes = models.TextField('Notes',blank=True,null=True)
    def __str__(self):
        return self.dept_long_name

class Bank(models.Model):
    bank_long_name = models.CharField('Name of Bank',max_length=250,blank=False,null=False)
    bank_short_name = models.CharField('Bank Short Name',max_length=50,blank=True,null=True)
    bank_notes = models.TextField('Notes',blank=True,null=True)
    def __str__(self):
        return self.bank_short_name

class BankBranch(models.Model):
    branch_name = models.CharField('Name of Branch',max_length=250,blank=False,null=False)
    bank_code = models.ForeignKey(Bank,on_delete=models.CASCADE,blank=False,null=False)
    branch_location = models.CharField('Branch Location',max_length=250,blank=False,null=False)
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
    job_rank = models.CharField("Job Title Rank",max_length=150,blank=True,null=True,choices=STAFFLEVEL)   #(Snr Staff, Jnr Staff, Exec., Mgt, etc)
    salary_level = models.CharField("Salary Level",max_length=150,blank=True,null=True)
    jobtitle_notes = models.TextField("Notes",blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True) 
