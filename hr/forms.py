from django.forms import ModelForm # type: ignore
from .models import *


class EmployeeForm(ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        exclude = ['updated','created']
        
class CompanyInformationForm(ModelForm):
    class Meta:
        model = CompanyInformation
        fields = '__all__'
        exclude = ['updated','created']

class StaffSchoolForm(ModelForm):
    class Meta:
        model = Staff_School
        fields = '__all__'
        exclude = ['updated','created']

class StaffCompanyForm(ModelForm):
    class Meta:
        model = Prev_Company
        fields = '__all__'
        exclude = ['updated','created']

class KithForm(ModelForm):
    class Meta:
        model = Kith
        fields = '__all__'
        exclude = ['updated','created']

class ResAddressForm(ModelForm):
    class Meta:
        model = Res_Address
        fields = '__all__'
        exclude = ['updated','created']

class PostAddressForm(ModelForm):
    class Meta:
        model = Postal_Address
        fields = '__all__'
        exclude = ['updated','created']

class VehicleForm(ModelForm):
    class Meta:
        model = Vehicle
        fields = '__all__'
        exclude = ['updated','created']

class StaffBankForm(ModelForm):
    class Meta:
        model = StaffBank
        fields = '__all__'
        exclude = ['updated','created']

class PromotionForm(ModelForm):
    class Meta:
        model = Promotion
        fields = '__all__'
        exclude = ['updated','created']

class TransferForm(ModelForm):
    class Meta:
        model = Transfer
        fields = '__all__'
        exclude = ['updated','created']

class BereavementForm(ModelForm):
    class Meta:
        model = Bereavement
        fields = '__all__'
        exclude = ['updated','created']

class MarriageForm(ModelForm):
    class Meta:
        model = Marriage
        fields = '__all__'
        exclude = ['updated','created']

class ChristeningForm(ModelForm):
    class Meta:
        model = Christening
        fields = '__all__'
        exclude = ['updated','created']

class CelebrationForm(ModelForm):
    class Meta:
        model = Celebration
        fields = '__all__'
        exclude = ['updated','created']