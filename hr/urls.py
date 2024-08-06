from django.urls import path # type: ignore

from . import views

urlpatterns = [
    path('', views.landing,name="landing"),
    path('login', views.index,name="login"),
    path('register', views.register,name="register"),
    path('logout', views.logoutUser,name="logout"),
    path('search', views.search,name="search"),
    path('newstaff', views.newstaff,name="newstaff"),
    path('allstaff', views.allstaff,name="allstaff"),
    path('edit_staff/<str:staffno>', views.edit_staff,name="edit-staff"),
    path('delete_staff/<str:staffno>', views.deletestaff,name="delete-staff"),
    path('staff_details/<str:staffno>', views.staff_details,name="staff-details"),

    path('company_info/<str:staffno>', views.company_info,name="company-info"),
    path('edit_company_info/<str:staffno>', views.edit_company_info,name="edit-company-info"),
    # path('delete_company_info/<str:staffno>', views.delete_company_info,name="delete-company-info"),

    path('emp_relation/<str:staffno>', views.emp_relation,name="emp_relation"),
    path('edit_emp_relation/<str:staffno>', views.edit_emp_relation,name="edit-emp-relation"),
    
    path('staff_education/<str:staffno>', views.staff_education,name="staff-education"),
    path('edit_staff_education/<str:sch_id>/<str:staffno>', views.edit_staff_education,name="edit-staff-education"),
    path('delete_staff_education/<str:sch_id>/<str:staffno>', views.delete_staff_education,name="delete-staff-education"),

    path('prev_work/<str:staffno>', views.prev_work,name="prev-work"),
    path('edit_prev_work/<str:coy_id>/<str:staffno>', views.edit_prev_work,name="edit-prev-work"),
    path('delete_prev_work/<str:coy_id>/<str:staffno>', views.delete_prev_work,name="delete-prev-work"),

    path('dependants/<str:staffno>', views.dependants,name="dependants"),
    path('edit_dependants/<str:dep_id>/<str:staffno>', views.edit_dependants,name="edit-dependants"),
    path('delete_dependants/<str:dep_id>/<str:staffno>', views.delete_dependants,name="delete-dependants"),

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
]