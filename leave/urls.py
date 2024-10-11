from django.urls import path # type: ignore

from . import views

urlpatterns = [
    # path('leave', views.leave_entitlement,name="leave"),
    path('leave_request', views.leave_request, name="leave-request"),
    path('leave_entitlement', views.leave_entitlement, name="leave-entitlement"),
    path('leave_academic_year', views.leave_academic_year, name="leave-academic-year"),
    path('edit_leave_entitlement/<int:le_id>', views.edit_leave_entitlement, name="edit-leave-entitlement"),
    path('delete_leave_entitlement/<int:le_id>', views.delete_leave_entitlement, name="delete-leave-entitlement"),
    
    path('leave_report/', views.leave_report, name='leave-report'),

]