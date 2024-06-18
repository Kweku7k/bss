from django.forms import ModelForm # type: ignore
from .models import *


class SchoolForm(ModelForm):
    class Meta:
        model = School
        fields = '__all__'

class ProfBodyForm(ModelForm):
    class Meta:
        model = ProfBody
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