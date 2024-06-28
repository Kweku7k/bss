from django.db import models # type: ignore
from datetime import datetime, timezone
from hr.choices import *
from setup.models import *
# Create your models here.

class Employee(models.Model):
    staffno = models.CharField('Staff Number',max_length=12,blank=False,null=False,primary_key=True,unique=True)
    title = models.CharField('Title of Courtesy',max_length=20,blank=False,null=False)
    lname = models.CharField('Surname',max_length=120,blank=False,null=False)
    fname = models.CharField('First Name',max_length=120,blank=False,null=False)
    middlenames = models.CharField('Middle Names',max_length=120,blank=True,null=True)
    suffix = models.CharField('Name Suffixe',max_length=20,blank=True,null=True)
    gender = models.CharField(max_length=20)
    dob = models.DateField('Date of Birth')
    ssnitno = models.CharField('SSNIT No.',max_length=50,blank=True,null=True)
    gcardno = models.CharField('Ghana Card No.',max_length=50,blank=True,null=True)
    heq = models.CharField('Highest Academic Qualification',max_length=100,blank=True,null=True)
    hpq = models.CharField('Highest Professional Qualification',max_length=100,blank=True,null=True)
    active_phone = models.CharField('Active Phone No.',max_length=15,blank=True,null=True)
    active_status = models.CharField('Staff Status',max_length=25,blank=False,default='Active',null=False)
    home_town = models.CharField('Home Town',max_length=100,blank=True,null=True)
    region  = models.CharField('Region',max_length=50,blank=True,null=True)
    rba = models.CharField('Role-Based Access',max_length=10,blank=False,default='REG',null=False)
    doe = models.DateField('Date Employed')
    staff_rank = models.CharField('Staff Rank',max_length=50,blank=True,null=True)
    job_title = models.CharField('Job Title',max_length=50,blank=True,null=True)
    staff_pix = models.ImageField(upload_to='images/', blank=True,null=True)
    email_address= models.EmailField(blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        staffname = self.title + ' '
        if self.fname:
            staffname += self.fname + ' '
        if self.middlenames:
            staffname += self.middlenames + ' '
        if self.lname:
            staffname += self.lname + ' '
        if self.suffix:
            staffname += self.suffix 
        return staffname
        #self.title + ' ' + self.fname + ' ' + self.middlenames + ' ' + self.lname + ' ' + self.suffix

class Rank(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
class ChoicesHPQ(models.Model):
    name = models.CharField(max_length=120, unique=True)
    
class ChoicesRegion(models.Model):
    name = models.CharField(max_length=120, unique=True)
    
class ChoicesDependants(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ChoicesHEQ(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ChoicesTitle(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ChoicesSuffix(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ChoicesRBA(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ChoicesStaffLevel(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ChoicesStaffRank(models.Model):
    name = models.CharField(max_length=120, unique=True)
    
class ChoicesGender(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ChoicesStaffStatus(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ProfessionalBody(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE) # Link to Employees model
    assoc_code = models.CharField(ProfBody,max_length=50,blank=False,null=False) #Link this to the Prof. Body
    membershipno = models.CharField('Membership Number',max_length=20,blank=False,null=False)
    date_joined = models.DateField('Date Joined')
    hra = models.ForeignKey(Rank, on_delete=models.SET_DEFAULT, default=1)  # Use ForeignKey to Rank model
    # hra = models.CharField('Highest Rank Attained',max_length=50,blank=False,default='Member',null=False)
    notes = models.TextField('Notes',blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.assoc_code
    
class Res_Address(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE) # Link to Employees model
    house_no = models.CharField('House Number',max_length=50,blank=True,null=True)
    street_name = models.CharField('Street Name',max_length=50,blank=True,null=True)
    town = models.CharField('Town',max_length=50,blank=True,null=True)
    landmark = models.CharField('Nearest Landmark',max_length=100,blank=True,null=True)
    gps_address = models.CharField('GPS Address',max_length=50,blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        resadd = self.house_no + ', '
        if self.street_name:
            resadd += self.street_name + ', '
        if self.town:
            resadd +=  self.town
        return resadd

class Postal_Address(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE) # Link to Employees model
    box_no = models.CharField('P.O.Box Number',max_length=50,blank=True,null=True)
    town = models.CharField('Town',max_length=50,blank=True,null=True)
    care_of = models.CharField('C/O',max_length=100,blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.box_no + ' ' +  self.town
    
class Staff_School(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE) # Link to Employees model
    school_code = models.ForeignKey(School,blank=False,null=False,on_delete=models.CASCADE) # Link to Setup.School model (Import School from Setup into this file)
    prog_studied = models.CharField('Program of Study',max_length=100,blank=True,null=True)
    start_date = models.DateField()
    finish_date = models.DateField()
    any_post = models.CharField('Position Held',max_length=250,blank=True,null=True)
    certification = models.CharField('Certification',max_length=250,blank=True,null=True)
    notes = models.TextField('Notes',blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    
class Medical(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE) # Link to Employees model
    hospital_code = models.ForeignKey(Hospital,blank=False,null=False,on_delete=models.CASCADE)
    date_attended = models.DateField()
    complaint = models.CharField(max_length=100,blank=True,null=True)
    patient_name = models.CharField(max_length=100,blank=False,null=False)
    relationship = models.CharField(max_length=120) # Select from Self, Spouse, Child
    treatment_cost = models.IntegerField()
    quota_balance = models.IntegerField()
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

class Kith(models.Model):
     staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE) 
     kith_lname = models.CharField('Surname',max_length=120,blank=False,null=False)
     kith_fname = models.CharField('First Name',max_length=120,blank=False,null=False)
     kith_middlenames = models.CharField('Middle Names',max_length=120,blank=True,null=True)
     kith_relationship = models.CharField(max_length=120)
     kith_gender = models.CharField(max_length=120)
     kith_dob = models.DateField('Date of Birth')
     updated = models.DateTimeField(auto_now=True)
     created = models.DateTimeField(auto_now_add=True)
     def __str__(self):
        f_name = self.kith_fname
        if self.kith_middlenames:
            f_name +=  ' ' +  self.kith_middlenames
        f_name +=  ' ' +  self.kith_lname
        return f_name #self.kith_fname + ' ' +  self.kith_middlenames + ' ' +  self.kith_lname
     
class StaffBank(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE) 
    bank = models.ForeignKey(Bank,blank=False,null=False,on_delete=models.CASCADE)
    branch = models.ForeignKey(BankBranch,blank=False,null=False,on_delete=models.CASCADE)
    account_no = models.CharField(max_length=20,blank=False,null=False)
    account_type = models.CharField(max_length=20,blank=False,null=False,default='Current')   #choices=(('Savings','Savings'),('Current','Current'))
    account_status= models.CharField(max_length=20,blank=False,null=False, default='Active')   #choices=(('Active','Active'),('Inactive','Inactive'))
    account_date=models.DateField()
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

class Prev_Company(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    coy_name = models.CharField('Company Name',max_length=120,blank=False,null=False)
    start_date = models.DateField()
    end_date = models.DateField()
    termination_reason = models.CharField('Reason for Leaving',max_length=120,blank=False,null=False)
    highest_position = models.CharField('Highest Position',max_length=120,blank=False,null=False)
    highest_salary = models.BigIntegerField()
    contact_name = models.CharField('Contact Name',max_length=120,blank=True,null=True)
    contact_phone = models.CharField('Contact Phone',max_length=120,blank=True,null=True)
    notes = models.TextField('Notes',blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

class Vehicle(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    car_no = models.CharField('Car No',max_length=20,blank=False,null=False)
    record_date = models.DateField(auto_now=True)
    car_model = models.CharField('Car Model',max_length=100,blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

class Promotion(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    prev_jobtitle = models.CharField('Previous Job Title',max_length=100,blank=False,null=False)
    new_jobtitle = models.CharField('New Job Title',max_length=100,blank=False,null=False)
    prev_rank  = models.CharField('Previous Rank',max_length=100,blank=False,null=False)
    new_rank = models.CharField('New Rank',max_length=100,blank=False,null=False)
    effective_date = models.DateField()
    approved_by = models.CharField('Approved By',max_length=100,blank=False,null=False)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

class Transfer(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    prev_office = models.CharField('Previous Office',max_length=100,blank=False,null=False)
    new_office = models.CharField('New Office',max_length=100,blank=False,null=False)
    prev_dept  = models.CharField('Previous Department',max_length=100,blank=False,null=False)
    new_dept = models.CharField('New Department',max_length=100,blank=True,null=True)
    effective_date = models.DateField()
    approved_by = models.CharField('Approved By',max_length=100,blank=False,null=False)
    prev_branch = models.CharField('Previous Branch',max_length=100,blank=True,null=True)
    new_branch = models.CharField('New Branch',max_length=100,blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True) 

class Bereavement(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    deceased = models.CharField('Deceased',max_length=100,blank=False,null=False)
    deceased_relationship = models.CharField('Relationship',max_length=100,blank=False,null=False)
    funeral_date = models.DateField()
    funeral_time = models.CharField('Funeral Time',max_length=50,blank=True,null=True)
    funeral_location = models.CharField('Location',max_length=100,blank=False,null=False)
    funeral_dress_code = models.CharField('Dress Code',max_length=60,blank=True,null=True)
    deceased_pix = models.ImageField(upload_to='images/funeral/', blank=True,null=True)
    funeral_notes = models.TextField('Notes',blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True) 

class Marriage(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    celebrant = models.CharField('Celebrant',max_length=100,blank=False,null=False)
    relationship = models.CharField('Relationship',max_length=100,blank=True,null=True)
    marriage_date = models.DateField()
    marriage_time = models.CharField('Time',max_length=50,blank=True,null=True)
    marriage_location = models.CharField('Location',max_length=100,blank=False,null=False)
    marriage_dress_code = models.CharField('Dress Code',max_length=100,blank=True,null=True)
    marriage_pix = models.ImageField(upload_to='images/marriage/', blank=True,null=True)
    marriage_notes = models.TextField('Notes',blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True) 

class Christening(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    chris_location = models.CharField('Location',max_length=100,blank=False,null=False)
    chris_date = models.DateField()
    chris_dress_code = models.CharField('Dress Code',max_length=100,blank=True,null=True)
    chris_time = models.CharField('Time',max_length=50,blank=True,null=True)
    chris_notes = models.TextField('Notes',blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True) 

class Celebration(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    cel_location = models.CharField('Location',max_length=100,blank=False,null=False)
    cel_occassion = models.CharField('Occasion',max_length=200,blank=False,null=False)
    cel_date = models.DateField()
    cel_dress_code = models.CharField('Dress Code',max_length=100,blank=True,null=True)
    cel_time = models.CharField('Time',max_length=50,blank=True,null=True)
    cel_notes = models.TextField('Notes',blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True) 