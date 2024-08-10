from django.urls import path # type: ignore

from . import views

urlpatterns = [
    path('leave', views.leave_entitlement,name="leave"),
    
    path('leave_request', views.leave_request, name="leave-request"),

]