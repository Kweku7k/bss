from django.forms import ModelForm # type: ignore
from .models import *
from hr.models import *


class SchoolForm(ModelForm):
    class Meta:
        model = School
        fields = '__all__'

class ProfBodyForm(ModelForm):
    class Meta:
        model = ProfBody
        fields = '__all__'
        
class TitleForm(ModelForm):
    class Meta:
        model = Title
        fields = '__all__'
        
class QualificationForm(ModelForm):
    class Meta:
        model = Qualification
        fields = '__all__'
        
class StaffCategoryForm(ModelForm):
    class Meta:
        model = StaffCategory
        fields = '__all__'
        
class ContractForm(ModelForm):
    class Meta:
        model = Contract
        fields = '__all__'
        
class CampusForm(ModelForm):
    class Meta:
        model = Campus
        fields = '__all__'
        
class DirectorateForm(ModelForm):
    class Meta:
        model = Directorate
        fields = '__all__'
        
class School_FacultyForm(ModelForm):
    class Meta:
        model = School_Faculty
        fields = '__all__'

class DepartmentForm(ModelForm):
    class Meta:
        model = Department
        fields = '__all__'

class HospitalForm(ModelForm):
    class Meta:
        model = Hospital
        fields = '__all__'

class BankForm(ModelForm):
    class Meta:
        model = Bank
        fields = '__all__'

class BankBranchForm(ModelForm):
    class Meta:
        model = BankBranch
        fields = '__all__'

class StaffRankForm(ModelForm):
    class Meta:
        model = StaffRank
        fields = '__all__'

class JobTitleForm(ModelForm):
    class Meta:
        model = JobTitle
        fields = '__all__'
        exclude = ['updated','created']