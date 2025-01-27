from venv import logger
from django.db import models # type: ignore
from datetime import datetime, timezone
from hr.choices import *
from setup.models import *
from django.contrib.auth.models import AbstractUser
# from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib import messages





# Create your models here.

class Employee(models.Model):
    staffno = models.CharField('Staff Number',max_length=12,blank=False,null=False,primary_key=True,unique=True)
    title = models.CharField('Title',max_length=20,blank=False,null=False)
    lname = models.CharField('Surname',max_length=120,blank=False,null=False)
    fname = models.CharField('First Name',max_length=120,blank=False,null=False)
    middlenames = models.CharField('Middle Names',max_length=120,blank=True,null=True)
    oname = models.CharField('Other Names', max_length=120, blank=True, null=True)
    suffix = models.CharField('Name Suffixe',max_length=20,blank=True,null=True)
    gender = models.CharField(max_length=20)
    dob = models.DateField('Date of Birth')
    m_status = models.CharField('Marital Status',max_length=50,blank=True,null=True)
    nationality = models.CharField('Nationality',max_length=50,blank=True,null=True)
    ethnic = models.CharField('Ethnic Group',max_length=50,blank=True,null=True)
    home_town = models.CharField('Home Town',max_length=100,blank=True,null=True)
    region  = models.CharField('Region',max_length=50,blank=True,null=True)
    pob  = models.CharField('Place of Birth',max_length=50,blank=True,null=True)
    religion  = models.CharField('Religion',max_length=50,blank=True,null=True)
    denomination  = models.CharField('Denomination',max_length=50,blank=True,null=True)
    email_address= models.EmailField('Persoanl Email',max_length=50,blank=True,null=True)
    active_phone = models.CharField('Active Phone No.',max_length=15,blank=True,null=True)
    ssnitno = models.CharField('SSNIT No.',max_length=50,blank=True,null=True)
    idtype = models.CharField('ID Type',max_length=50,blank=True,null=True)
    gcardno = models.CharField('ID Card No.',max_length=50,blank=True,null=True)
    digital = models.CharField('Digital Address',max_length=100,blank=True,null=True)
    residential = models.CharField('Residential Address',max_length=100,blank=True,null=True)
    postal = models.CharField('Postal Address',max_length=100,blank=True,null=True)
    blood = models.CharField('Blood Group',max_length=50,blank=True,null=True)
    car = models.CharField('Car Number',max_length=50,blank=True,null=True)
    chassis = models.CharField('Chassis Number',max_length=50,blank=True,null=True)
    vech_type = models.CharField('Vechicle Type',max_length=50,blank=True,null=True)
    study_area = models.CharField('Area of Study',max_length=50,blank=True,null=True)
    heq = models.CharField('Highest Academic Qualification',max_length=100,blank=True,null=True)
    completion_year = models.CharField('Year of Completion',max_length=100,blank=True,null=True)
    institution = models.CharField('Institution of Study',max_length=100,blank=True,null=True)
    other_heq = models.CharField('Other Educational Qualification',max_length=100,blank=True,null=True)
    hpq = models.CharField('Highest Professional Qualification',max_length=100,blank=True,null=True)
    staff_pix = models.ImageField(upload_to='images/', blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.staffno} {self.title} {self.fname or ''} {self.lname or ''}".strip()
    
    def calculate_age(self):
        if self.dob:
            today = datetime.today()
            return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
        return None



class CompanyInformation(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE) # Link to Employees model
    job_title = models.CharField('Job Title',max_length=50,blank=True,null=True)
    job_description = models.TextField('Job Description',max_length=200,blank=True,null=True)
    staff_cat = models.CharField('Staff Category',max_length=100,blank=True,null=True)
    contract = models.CharField('Contract',max_length=50,blank=True,null=True)
    active_status = models.CharField('Staff Status',max_length=50,blank=True,null=True)
    doa = models.DateField('Date of Appointment', blank=True,null=True)
    doe = models.DateField('Date of Expiration', blank=True,null=True)
    renewal = models.DateField('Renewal', blank=True,null=True)
    rank = models.CharField('Designation/Rank',max_length=50,blank=True,null=True)
    campus = models.CharField('Campus',max_length=50,blank=True,null=True)
    city = models.CharField('City',max_length=50,blank=True,null=True)
    email = models.CharField('Official Email',max_length=50,blank=True,null=True)
    sch_fac_dir = models.CharField('School Faculty',max_length=150,blank=True,null=True)
    dept = models.CharField('Department',max_length=100,blank=True,null=True)
    directorate = models.CharField('Directorate',max_length=100,blank=True,null=True)
    salary = models.CharField('Salary',max_length=50,blank=True,null=True)
    cost_center = models.CharField('Cost Center',max_length=100,blank=True,null=True)
    bank_name = models.CharField('Bank Name',max_length=100,blank=True,null=True)
    accno = models.CharField('Account Number',max_length=50,blank=True,null=True)
    bank_branch = models.CharField('Bank Branch',max_length=100,blank=True,null=True)
    ssn_con = models.CharField('SSN Contributor',max_length=10,blank=True,null=True)
    pf_con = models.CharField('PF Contributor',max_length=10,blank=True,null=True)
   
    
    def __str__(self):
        return self.staffno
    
class Kith(models.Model):
     staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE) 
     kith_lname = models.CharField('Surname',max_length=120,blank=True,null=True)
     kith_fname = models.CharField('First Name',max_length=120,blank=True,null=True)
     kith_middlenames = models.CharField('Middle Names',max_length=120,blank=True,null=True)
     kith_relationship = models.CharField(max_length=50,blank=True,null=True)
     kith_gender = models.CharField(max_length=50,blank=True,null=True)
     kith_dob = models.DateField('Date of Birth')
     phone = models.CharField('Phone No.',max_length=15,blank=True,null=True)
     residential = models.CharField('Residential Address',max_length=100,blank=True,null=True)
     status = models.CharField('Dead or Alive',max_length=10,blank=True,null=True)
     kin = models.CharField('Next of Kin',max_length=10,blank=True,null=True)
     ben = models.CharField('Beneficiary',max_length=100,blank=True,null=True)
     percentage = models.IntegerField('Beneficiary',validators=[ MinValueValidator(0), MaxValueValidator(100) ],blank=True,null=True)
     updated = models.DateTimeField(auto_now=True)
     created = models.DateTimeField(auto_now_add=True)
     def __str__(self):
        return self.kith_fname
     


class User(AbstractUser): 
    staffno = models.CharField(max_length=50, blank=False, null=False, unique=True)
    approval = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.staffno})"


class Rank(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
class ChoicesHPQ(models.Model):
    name = models.CharField(max_length=120, unique=True)
    
class ChoicesRegion(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ChoicesLeaveType(models.Model):
    name = models.CharField(max_length=120, unique=True)  
    deductible = models.BooleanField(default=False)


class ChoicesDependants(models.Model):
    name = models.CharField(max_length=120, unique=True)
    
class ChoicesRelationStatus(models.Model):
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
    
class ChoicesReligion(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ChoicesDenomination(models.Model):
    name = models.CharField(max_length=120, unique=True)
    
class ChoicesIdType(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ChoicesMaritalStatus(models.Model):
    name = models.CharField(max_length=120, unique=True)
    
class ChoicesMedicalTreatment(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
class ChoicesMedicalType(models.Model):
    name = models.CharField(max_length=100, unique=True)

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
    school_code = models.CharField('Institution',max_length=250,blank=True,null=True) 
    prog_studied = models.CharField('Program of Study',max_length=100,blank=True,null=True)
    start_date = models.DateField()
    finish_date = models.DateField()
    any_post = models.CharField('Position Held',max_length=250,blank=True,null=True)
    certification = models.CharField('Certification',max_length=250,blank=True,null=True)
    notes = models.TextField('Notes',blank=True,null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    

class Staff_Leave(models.Model):
    staffno = models.ForeignKey(Employee, blank=False, null=False, on_delete=models.CASCADE) # Link to Employees model
    staff_cat = models.CharField('Staff Category',max_length=100,blank=True,null=True)
    leave_type = models.CharField('Type of Leave', max_length=100, blank=True, null=True)
    academic_year = models.CharField('AcademicYear', max_length=20, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    days_taken = models.IntegerField()
    reason = models.TextField('Reason for Leave', blank=True, null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    
    
class Medical(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    staff_cat = models.CharField('Staff Category',max_length=100,blank=True,null=True)
    hospital_code = models.CharField('Hospital', max_length=100, blank=True, null=True)
    payment_type = models.CharField('Payment Type', max_length=100, blank=True, null=True)
    nature = models.CharField('Nature of Treatment', max_length=100, blank=True, null=True)
    academic_year = models.CharField('AcademicYear', max_length=20, blank=True, null=True)
    date_attended = models.DateField()
    complaint = models.TextField(max_length=300,blank=True,null=True)
    patient_name = models.CharField(max_length=100,blank=True,null=True)
    relationship = models.CharField(max_length=20, blank=True, null=True) # Select from Self, Spouse, Child
    treatment_cost = models.DecimalField(max_digits=10, decimal_places=3)
    other = models.CharField(max_length=100, blank=True, null=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)


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
    
    
class RenewalHistorys(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    effective_date = models.DateField()
    end_date = models.DateField(blank=True,null=True)
    prev_staff_category = models.CharField(max_length=120,blank=True,null=True)
    new_staff_category = models.CharField(max_length=120,blank=True,null=True)
    prev_job_title = models.CharField(max_length=120,blank=True,null=True)
    new_job_title = models.CharField(max_length=120,blank=True,null=True)
    prev_position = models.CharField(max_length=120,blank=True,null=True)
    new_position = models.CharField(max_length=120,blank=True,null=True)
    is_approved = models.BooleanField(default=False)
    is_disapproved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_renewals')

    def __str__(self):
        return f"Renewal for {self.staffno} from {self.start_date} to {self.end_date}"
    
@receiver(post_save, sender=RenewalHistorys)
def update_company_info_on_approval_or_disapproval(sender, instance, **kwargs):
    company_info = CompanyInformation.objects.filter(staffno=instance.staffno).first()
    if not company_info:
        messages.error(f"No company information found for staff {instance.staffno}")
    else:
        if instance.is_approved:
            if company_info:
                company_info.job_title = instance.new_job_title
                company_info.staff_cat = instance.new_staff_category
                company_info.rank = instance.new_position
                company_info.doe = instance.end_date
                company_info.save()
        elif instance.is_disapproved:
            if company_info:
                company_info.job_title = instance.prev_job_title
                company_info.staff_cat = instance.prev_staff_category
                company_info.rank = instance.prev_position
                company_info.save()
            

class PromotionHistory(models.Model):
    staffno = models.ForeignKey(Employee,blank=False,null=False,on_delete=models.CASCADE)
    effective_date = models.DateField()
    end_date = models.DateField()
    prev_staff_category = models.CharField(max_length=120,blank=True,null=True)
    new_staff_category = models.CharField(max_length=120,blank=True,null=True)
    prev_job_title = models.CharField(max_length=120,blank=True,null=True)
    new_job_title = models.CharField(max_length=120,blank=True,null=True)
    prev_position = models.CharField(max_length=120,blank=True,null=True)
    new_position = models.CharField(max_length=120,blank=True,null=True)
    is_approved = models.BooleanField(default=False)
    is_disapproved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_promotions')

    def __str__(self):
        return f"Promotion for {self.staffno} from {self.prev_staff_category} to {self.new_staff_category}"
    
@receiver(post_save, sender=PromotionHistory)
def update_company_info_on_approval_or_disapproval(sender, instance, **kwargs):
    company_info = CompanyInformation.objects.filter(staffno=instance.staffno).first()
    if not company_info:
        messages.error(f"No company information found for staff {instance.staffno}")
    else:
        if instance.is_approved:
            if company_info:
                company_info.job_title = instance.new_job_title
                company_info.staff_cat = instance.new_staff_category
                company_info.rank = instance.new_position
                company_info.doe = instance.end_date
                company_info.save()
        elif instance.is_disapproved:
            if company_info:
                company_info.job_title = instance.prev_job_title
                company_info.staff_cat = instance.prev_staff_category
                company_info.rank = instance.prev_position
                company_info.save()        
    