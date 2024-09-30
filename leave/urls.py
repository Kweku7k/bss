from django.urls import path # type: ignore

from . import views

urlpatterns = [
    # path('leave', views.leave_entitlement,name="leave"),
    path('leave_request', views.leave_request, name="leave-request"),
    path('leave_entitlement', views.leave_entitlement, name="leave-entitlement"),
    path('edit_leave_entitlement/<int:le_id>', views.edit_leave_entitlement, name="edit-leave-entitlement"),
    path('delete_leave_entitlement/<int:le_id>', views.delete_leave_entitlement, name="delete-leave-entitlement")
]