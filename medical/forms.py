from django.forms import ModelForm # type: ignore
from .models import *

class MedicalEntitlementForm(ModelForm):
    class Meta:
        model = MedicalEntitlement
        fields = '__all__'
        exclude = ['updated','created']