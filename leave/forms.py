from django.forms import ModelForm # type: ignore
from .models import *


class LeaveForm(ModelForm):
    class Meta:
        model = Leave
        fields = '__all__'
        exclude = ['updated','created']
        
class LeaveEntitlementForm(ModelForm):
    class Meta:
        model = LeaveEntitlement
        fields = ['staff_cat', 'entitlement', 'academic_year']
        
class AcademicYearForm(ModelForm):
    class Meta:
        model = AcademicYear
        fields = '__all__'
        exclude = ['updated','created']