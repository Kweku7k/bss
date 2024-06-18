from django.urls import path # type: ignore

from . import views

urlpatterns = [
    path('', views.home,name="home"),
    path('school', views.add_school,name="add-school"),
    path('edit_school/<int:sch_id>', views.edit_school,name="edit-school"),
    path('delete_school/<int:sch_id>', views.delete_sch,name="delete-school"),

    path('profbody', views.add_profbody,name="add-profbody"),
    path('edit_profbody/<int:pb_id>', views.edit_profbody,name="edit-profbody"),
    path('delete_profbody/<int:pb_id>', views.delete_profbody,name="delete-profbody"),

    path('dept', views.add_dept,name="add-dept"),
    path('edit_dept/<int:dept_id>', views.edit_dept,name="edit-dept"),
    path('delete_dept/<int:dept_id>', views.delete_dept,name="delete-dept"),

    path('hosp', views.add_hosp,name="add-hosp"),
    path('edit_hosp/<int:hosp_id>', views.edit_hosp,name="edit-hosp"),
    path('delete_hosp/<int:hosp_id>', views.delete_hosp,name="delete-hosp"),

    path('bank', views.add_bank,name="add-bank"),
    path('edit_bank/<int:bank_id>', views.edit_bank,name="edit-bank"),
    path('delete_bank/<int:bank_id>', views.delete_bank,name="delete-bank"),

    path('bankbranch', views.add_bankbranch,name="add-bankbranch"),
    path('edit_bankbranch/<int:bankbranch_id>/<int:bankid>', views.edit_bankbranch,name="edit-bankbranch"),
    path('delete_bankbranch/<int:bankbranch_id>', views.delete_bankbranch,name="delete-bankbranch"),

    path('jobtitle', views.add_jobtitle,name="add-jobtitle"),
    path('edit_jobtitle/<int:jobtitle_id>', views.edit_jobtitle,name="edit-jobtitle"),
    path('delete_jobtitle/<int:jobtitle_id>', views.delete_jobtitle,name="delete-jobtitle"),
]