from django import forms
from django.forms import ModelForm # type: ignore
from .models import *
from django.contrib.auth.forms import UserCreationForm, UserChangeForm


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label='Select a CSV file', widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
        
class RegistrationForm(UserCreationForm):   
    class Meta:
        model = User
        fields = ['username', 'email', 'staffno', 'password1', 'password2']
        # add helpertext to display errors
        

class UserUpdateForm(UserChangeForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'staffno', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
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


class LeaveTransactionForm(ModelForm):
    class Meta:
        model = Staff_Leave
        fields = '__all__'
        exclude = ['updated','created']
        
class MedicalTransactionForm(ModelForm):
    class Meta:
        model = Medical
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
    
    
class RenewalHistoryForm(ModelForm):
    class Meta:
        model = RenewalHistorys
        fields = '__all__'
        exclude = ['updated', 'created']
        
        
class PromotionHistoryForm(ModelForm):
    class Meta:
        model = PromotionHistory
        fields = '__all__'
        exclude = ['updated', 'created']
        
        
class ExitHistoryForm(ModelForm):
    class Meta:
        model = Exits
        fields = '__all__'
        exclude = ['updated', 'created']
        
        
class StaffIncomeForm(ModelForm):
    class Meta:
        model = StaffIncome
        fields = '__all__'
        exclude = ['updated', 'created']
        
        
class StaffDeductionForm(ModelForm):
    class Meta:
        model = StaffDeduction
        fields = '__all__'
        exclude = ['updated', 'created']
        
class PayrollForm(ModelForm):
    class Meta:
        model = Payroll
        fields = '__all__'
        exclude = ['updated', 'created']