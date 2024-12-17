from django.urls import path # type: ignore

from . import views

urlpatterns = [
    # path('medical_form', views.medical_request, name="medical-form"),
    # path('request_medical', views.request_medical, name="request-medical"),
    # path('medical_report/', views.medical_report, name='medical-report'),
    path('medical_entitlement', views.medical_entitlement, name="medical-entitlement"),
    path('edit_medical_entitlement/<int:me_id>', views.edit_medical_entitlement, name="edit-medical-entitlement"),
    path('delete_medical_entitlement/<int:me_id>', views.delete_medical_entitlement, name="delete-medical-entitlement"),
    
    # path('medical_academic_year', views.medical_academic_year, name="medical-academic-year"),
    # path('edit_medical_academic_year/<int:ay_id>', views.edit_medical_academic_year, name="edit-medical-academic-year"),
    # path('delete_medical_academic_year/<int:ay_id>', views.delete_medical_academic_year, name="delete-medical-academic-year"),
]
