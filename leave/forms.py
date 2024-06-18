from django.forms import ModelForm # type: ignore
from .models import *


class LeaveForm(ModelForm):
    class Meta:
        model = Leave
        fields = '__all__'
        exclude = ['updated','created']