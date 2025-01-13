from django.urls import path # type: ignore

from . import views

urlpatterns = [
    # path('leave', views.leave_entitlement,name="leave"),
    path('leave_form', views.leave_request, name="leave-form"),
    path('request_leave', views.request_leave, name="request-leave"),
    path('leave_entitlement', views.leave_entitlement, name="leave-entitlement"),
    path('edit_leave_entitlement/<int:le_id>', views.edit_leave_entitlement, name="edit-leave-entitlement"),
    path('delete_leave_entitlement/<int:le_id>', views.delete_leave_entitlement, name="delete-leave-entitlement"),
    
    path('leave_report/', views.leave_report, name='leave-report'),
    path('general_leave_request/', views.general_leave_request, name='general-leave-request'),
    path('get_staff_details/<str:staffno>/', views.get_staff_details, name='get-staff-details'),
    
]