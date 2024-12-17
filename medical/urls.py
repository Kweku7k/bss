from django.urls import path # type: ignore

from . import views

urlpatterns = [
    path('medical_report/', views.medical_report, name='medical-report'),
    path('medical_entitlement', views.medical_entitlement, name="medical-entitlement"),
    path('edit_medical_entitlement/<int:me_id>', views.edit_medical_entitlement, name="edit-medical-entitlement"),
    path('delete_medical_entitlement/<int:me_id>', views.delete_medical_entitlement, name="delete-medical-entitlement"),

]
