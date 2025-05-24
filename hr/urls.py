from django.urls import include, path # type: ignore
from two_factor.urls import urlpatterns as tf_urls
from .models import *
from .forms import *

from . import views

urlpatterns = [
    path('', views.landing,name="landing"),
    path('logs/', views.view_logs, name='logs'),
    path('login', views.index,name="login"),
    path('account/2fa/', include(tf_urls, namespace='two_factor')),
    path('register', views.register,name="register"),
    path('logout', views.logoutUser,name="logout"),
    path('profile', views.user_profile,name="profile"),
    path('search', views.search,name="search"),
    path('newstaff', views.newstaff,name="newstaff"),
    path('allstaff', views.allstaff,name="allstaff"),
    path('dormant_staff', views.dormant_staff,name="dormant-staff"),
    path('edit_staff/<str:staffno>', views.edit_staff,name="edit-staff"),
    path('delete_staff/<str:staffno>', views.deletestaff,name="delete-staff"),
    path('staff_details/<str:staffno>', views.staff_details,name="staff-details"),
    # path('filter_staff', views.filter_staff, name="filter-staff"),

    path('company_info/<str:staffno>', views.company_info,name="company-info"),
    path('edit_company_info/<str:staffno>', views.edit_company_info,name="edit-company-info"),
    # path('delete_company_info/<str:staffno>', views.delete_company_info,name="delete-company-info"),
    path('get_bank_branches/<str:bank_name>/', views.get_bank_branches, name='get_bank_branches'),
    path('get_departments/<str:sch_name>/', views.get_departments, name='get_departments'),
    path('get_units_by_department/<str:dept_name>/', views.get_units_by_department, name='get_units_by_department'),
    path('get_units_by_directorate/<str:directorate_name>/', views.get_units_by_directorate, name='get_units_by_directorate'),

    path('upload/', views.bulk_upload, name='bulk_upload'),
    path('download-sample-csv/', views.download_csv, name='download_sample_csv'),
    
    path('test', views.test,name="test"),
    
    path('emp_relation/<str:staffno>', views.emp_relation,name="emp-relation"),
    path('edit_emp_relation/<str:emp_id>/<str:staffno>', views.edit_emp_relation,name="edit-emp-relation"),
    path('delete_emp_relation/<str:emp_id>/<str:staffno>', views.delete_emp_relation,name="delete-emp-relation"),

    path('education/<str:staffno>', views.education,name="education"),
    path('edit_education/<str:edu_id>/<str:staffno>', views.edit_education,name="edit-education"),
    path('delete_education/<str:edu_id>/<str:staffno>', views.delete_education,name="delete-education"),
    path('topnav/', views.topnav_view, name='topnav'),

    path('leave_transaction/<str:staffno>', views.leave_transaction, name="leave-transaction"),
    path('edit_leave_transaction/<str:lt_id>/<str:staffno>', views.edit_leave_transaction,name="edit-leave-transaction"),
    
    path('medical_transaction/<str:staffno>', views.medical_transaction, name="medical-transaction"),
    path('edit_medical_transaction/<str:med_id>/<str:staffno>', views.edit_medical_transaction, name="edit-medical-transaction"),
    
    path('staff_education/<str:staffno>', views.staff_education,name="staff-education"),
    path('edit_staff_education/<str:sch_id>/<str:staffno>', views.edit_staff_education,name="edit-staff-education"),
    path('delete_staff_education/<str:sch_id>/<str:staffno>', views.delete_staff_education,name="delete-staff-education"),

    path('prev_work/<str:staffno>', views.prev_work,name="prev-work"),
    path('edit_prev_work/<str:coy_id>/<str:staffno>', views.edit_prev_work,name="edit-prev-work"),
    path('delete_prev_work/<str:coy_id>/<str:staffno>', views.delete_prev_work,name="delete-prev-work"),

    # path('dependants/<str:staffno>', views.dependants,name="dependants"),
    # path('edit_dependants/<str:dep_id>/<str:staffno>', views.edit_dependants,name="edit-dependants"),
    # path('delete_dependants/<str:dep_id>/<str:staffno>', views.delete_dependants,name="delete-dependants"),

    path('res_address/<str:staffno>', views.res_address,name="res-address"),
    path('edit_res_address/<str:ra_id>/<str:staffno>', views.edit_res_address,name="edit-res-address"),
    path('delete_res_address/<str:ra_id>/<str:staffno>', views.delete_res_address,name="delete-res-address"),

    path('post_address/<str:staffno>', views.post_address,name="post-address"),
    path('edit_post_address/<str:post_id>/<str:staffno>', views.edit_post_address,name="edit-post-address"),
    path('delete_post_address/<str:post_id>/<str:staffno>', views.delete_post_address,name="delete-post-address"),

    path('vehicle/<str:staffno>', views.vehicle,name="vehicle"),
    path('edit_vehicle/<str:veh_id>/<str:staffno>', views.edit_vehicle,name="edit-vehicle"),
    path('delete_vehicle/<str:veh_id>/<str:staffno>', views.delete_vehicle,name="delete-vehicle"),

    path('staffbank/<str:staffno>', views.staffbank,name="staffbank"),
    path('edit_staffbank/<str:bk_id>/<str:staffno>', views.edit_staffbank,name="edit-staffbank"),
    path('delete_staffbank/<str:bk_id>/<str:staffno>', views.delete_staffbank,name="delete-staffbank"),
    
    path('promotion/<str:staffno>', views.promotion,name="promotion"),
    path('edit_promotion/<str:bk_id>/<str:staffno>', views.edit_promotion,name="edit-promotion"),
    path('delete_promotion/<str:bk_id>/<str:staffno>', views.delete_promotion,name="delete-promotion"),

    path('transfer/<str:staffno>', views.transfer,name="transfer"),
    path('edit_transfer/<str:bk_id>/<str:staffno>', views.edit_transfer,name="edit-transfer"),
    path('delete_transfer/<str:bk_id>/<str:staffno>', views.delete_transfer,name="delete-transfer"),
    
    path('bereavement/<str:staffno>', views.bereavement,name="bereavement"),
    path('edit_bereavement/<str:bno>/<str:staffno>', views.edit_bereavement,name="edit-bereavement"),
    path('delete_bereavement/<str:bno>/<str:staffno>', views.delete_bereavement,name="delete-bereavement"),

    path('marriage/<str:staffno>', views.marriage,name="marriage"),
    path('edit_marriage/<str:bno>/<str:staffno>', views.edit_marriage,name="edit-marriage"),
    path('delete_marriage/<str:bno>/<str:staffno>', views.delete_marriage,name="delete-marriage"),

    path('christening/<str:staffno>', views.christening,name="christening"),
    path('edit_christening/<str:bno>/<str:staffno>', views.edit_christening,name="edit-christening"),
    path('delete_christening/<str:bno>/<str:staffno>', views.delete_christening,name="delete-christening"),

    path('celebration/<str:staffno>', views.celebration,name="celebration"),
    path('edit_celebration/<str:bno>/<str:staffno>', views.edit_celebration,name="edit-celebration"),
    path('delete_celebration/<str:bno>/<str:staffno>', views.delete_celebration,name="delete-celebration"),
    
    path('renewal/<str:staffno>/', views.add_renewal_history, name='renewal-history'),
    path('renewals/approve/<int:renewal_id>/', views.approve_renewal, name='approve-renewal'),
    path('renewals/disapprove/<int:renewal_id>/', views.disapprove_renewal, name='disapprove-renewal'),

    path('promotion/<str:staffno>/', views.add_promotion_history, name='promotion-history'),
    path('promotion/approve/<int:promotion_id>/', views.approve_promotion, name='approve-promotion'),
    path('promotion/disapprove/<int:promotion_id>/', views.disapprove_promotion, name='disapprove-promotion'),
    
    
    # payroll url
    path('payroll/<str:staffno>', views.payroll_details, name="payroll-details"),
    path("payroll/processing/", views.payroll_processing, name="payroll-processing"),
    path('settings/<str:staffno>', views.staff_settings, name="staff-settings"),
    path('staff/<str:staffno>/mark-dormant/', views.mark_dormant, name='mark-dormant'),  
    
    # Roles and permission
    path('create_groups/', views.create_groups, name='create-groups'),
    path('groups/<int:group_id>/assign-permissions/', views.assign_permissions_to_group, name='assign-permissions'),
    path('assign_user_group/', views.assign_user_to_group, name='assign-user-group'),
    path('manage_users/', views.manage_users, name='manage-users'),


    path('user/approve/<int:user_id>/', views.approve_user, name='approve-user'),
    path('user/disapprove/<int:user_id>/', views.disapprove_user, name='disapprove-user'),
    
    path('create_staff_income/<str:staffno>', views.create_staff_income, name='create-staff-income'),
    path('edit_staff_income/<str:staffno>/<int:income_id>', views.edit_staff_income, name='edit-staff-income'),
    # path('delete_staff_income/<str:staffno>/<int:income_id>', views.delete_staff_income, name='delete-staff-income'),

    path('create_staff_deduction/<str:staffno>', views.create_staff_deduction, name='create-staff-deduction'),
    path('edit_staff_deduction/<str:staffno>/<int:deduction_id>', views.edit_staff_deduction, name='edit-staff-deduction'),
    # path('delete_staff_deduction/<str:staffno>/<int:deduction_id>', views.delete_staff_deduction, name='delete-staff-deduction'),
    
    
    
    path('new_dash/', views.new_landing, name='new-dash'),

]