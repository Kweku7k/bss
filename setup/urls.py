from django.urls import path # type: ignore
from hr.models import *
from . import views

urlpatterns = [
    path('', views.home,name="home"),
    path('school', views.add_school,name="add-school"),
    path('edit_school/<int:sch_id>', views.edit_school,name="edit-school"),
    path('delete_school/<int:sch_id>', views.delete_sch,name="delete-school"),

    path('profbody', views.add_profbody,name="add-profbody"),
    path('edit_profbody/<int:pb_id>', views.edit_profbody,name="edit-profbody"),
    path('delete_profbody/<int:pb_id>', views.delete_profbody,name="delete-profbody"),
    
    path('title', views.add_title,name="add-title"),
    path('edit_title/<int:title_id>', views.edit_title,name="edit-title"),
    path('delete_title/<int:title_id>', views.delete_title,name="delete-title"),
    
    path('qualification', views.add_qualification,name="add-qualification"),
    path('edit_qualification/<int:qual_id>', views.edit_qualification,name="edit-qualification"),
    path('delete_qualification/<int:qual_id>', views.delete_qualification,name="delete-qualification"),

    path('staffcategory', views.add_staffcategory,name="add-staffcategory"),
    path('edit_staffcategory/<int:sc_id>', views.edit_staffcategory,name="edit-staffcategory"),
    path('delete_staffcategory/<int:sc_id>', views.delete_staffcategory,name="delete-staffcategory"),
    
    path('contract', views.add_contract,name="add-contract"),
    path('edit_contract/<int:ct_id>', views.edit_contract,name="edit-contract"),
    path('delete_contract/<int:ct_id>', views.delete_contract,name="delete-contract"),
    
    path('campus', views.add_campus, name="add-campus"),
    path('edit_campus/<int:camp_id>', views.edit_campus, name="edit-campus"),
    path('delete_campus/<int:camp_id>', views.delete_campus, name="delete-campus"),

    path('directorate', views.add_directorate, name="add-directorate"),
    path('edit_directorate/<int:dict_id>', views.edit_directorate, name="edit-directorate"),
    path('delete_directorate/<int:dict_id>', views.delete_directorate, name="delete-directorate"),
    
    path('dept', views.add_dept,name="add-dept"),
    path('edit_dept/<int:dept_id>', views.edit_dept,name="edit-dept"),
    path('delete_dept/<int:dept_id>', views.delete_dept,name="delete-dept"),
    
    path('unit', views.add_unit,name="add-unit"),
    path('edit_unit/<int:unit_id>', views.edit_unit,name="edit-unit"),
    path('delete_unit/<int:unit_id>', views.delete_unit,name="delete-unit"),

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
    
    path('rank', views.add_staff_rank, name="add-rank"),
    path('edit_rank/<int:sr_id>', views.edit_staff_rank, name="edit-rank"),
    path('delete_rank/<int:sr_id>', views.delete_staff_rank, name="delete-rank"),
    
    path('academic_year', views.academic_year, name="academic-year"),
    path('edit_academic_year/<int:ay_id>', views.edit_academic_year, name="edit-academic-year"),
    path('delete_academic_year/<int:ay_id>', views.delete_academic_year, name="delete-academic-year"),
    
    path('salary_scale', views.salary_scale, name="add-salary-scale"),
    path('edit_salary_scale/<int:ss_id>', views.edit_salary_scale, name="edit-salary-scale"),
    path('delete_salary_scale/<int:ss_id>', views.delete_salary_scale, name="delete-salary-scale"),
    
    path('income_type', views.add_income_type, name="add-income-type"),
    path('edit_income_type/<int:it_id>', views.edit_income_type, name="edit-income-type"),
    path('delete_income_type/<int:it_id>', views.delete_income_type, name="delete-income-type"),
    
    path('deduction_type', views.add_deduction_type, name="add-deduction-type"),
    path('edit_deduction_type/<int:dt_id>', views.edit_deduction_type, name="edit-deduction-type"),
    path('delete_deduction_type/<int:dt_id>', views.delete_deduction_type, name="delete-deduction-type"),
        
    path('contribution_rate', views.add_contribution_rate, name="add-contribution-rate"),
    path('edit_contribution/<int:contrib_id>', views.edit_contribution, name="edit-contribution"),
    path('delete_contribution/<int:contrib_id>', views.delete_contribution, name="delete-contribution"),
    
    # Tax Band
    path('tax_band', views.add_tax_band, name="add-tax-band"),
    path('edit_tax_band/<int:tb_id>', views.edit_tax_band, name="edit-tax-band"),
    path('delete_tax_band/<int:tb_id>', views.delete_tax_band, name="delete-tax-band"),
    
    
    path('choices_hpq/', views.generic_model_crud, {'model_class': ChoicesHPQ, 'model_name': 'Professional Qualifications', 'template_name': 'setup/generic.html'}, name='choices-hpq'),
    path('choices_region/', views.generic_model_crud, {'model_class': ChoicesRegion, 'model_name': 'Region', 'template_name': 'setup/generic.html'}, name='choices-region'),
    path('choices_leave_type/', views.generic_model_crud, {'model_class': ChoicesLeaveType, 'model_name': 'Leave Type', 'template_name': 'setup/generic.html'}, name='choices-leave-type'),
    path('choices_dependants/', views.generic_model_crud, {'model_class': ChoicesDependants, 'model_name': 'Dependants', 'template_name': 'setup/generic.html'}, name='choices-dependants'),
    path('choices_relation_status/', views.generic_model_crud, {'model_class': ChoicesRelationStatus, 'model_name': 'Relation Status', 'template_name': 'setup/generic.html'}, name='choices-relation-status'),
    path('choices_suffix/', views.generic_model_crud, {'model_class': ChoicesSuffix, 'model_name': 'Suffix', 'template_name': 'setup/generic.html'}, name='choices-suffix'),
    path('choices_ethnic_group/', views.generic_model_crud, {'model_class': ChoicesRBA, 'model_name': 'Ethnic Group', 'template_name': 'setup/generic.html'}, name='choices-ethnic-group'),
    path('choices_gender/', views.generic_model_crud, {'model_class': ChoicesGender, 'model_name': 'Gender', 'template_name': 'setup/generic.html'}, name='choices-gender'),
    path('choices_marital_status/', views.generic_model_crud, {'model_class': ChoicesMaritalStatus, 'model_name': 'Marital Status', 'template_name': 'setup/generic.html'}, name='choices-marital-status'),
    path('choices_denomination/', views.generic_model_crud, {'model_class': ChoicesDenomination, 'model_name': 'Denomination', 'template_name': 'setup/generic.html'}, name='choices-denomination'),
    path('choices_religion', views.generic_model_crud, {'model_class': ChoicesReligion, 'model_name': 'Religion', 'template_name': 'setup/generic.html'}, name='choices-religion'),
    path('choices_id_type', views.generic_model_crud, {'model_class': ChoicesIdType, 'model_name': 'ID Type', 'template_name': 'setup/generic.html'}, name='choices-id-type'),
    path('choices_staff_status', views.generic_model_crud, {'model_class': ChoicesStaffStatus, 'model_name': 'Staff Status', 'template_name': 'setup/generic.html'}, name='choices-staff-status'),
    path('choices_medical_treatment', views.generic_model_crud, {'model_class': ChoicesMedicalTreatment, 'model_name': 'Nature of Treatment', 'template_name': 'setup/generic.html'}, name='choices-medical-treatment'),
    path('choices_medical_payment_type', views.generic_model_crud, {'model_class': ChoicesMedicalType, 'model_name': 'Medical Payment Type', 'template_name': 'setup/generic.html'}, name='choices-medical-payment-type'),
    path('choices_contribution', views.generic_model_crud, {'model_class': ChoicesContribution, 'model_name': 'Contribution', 'template_name': 'setup/generic.html'}, name='choices-contribution'),
    path('choices_exit_type', views.generic_model_crud, {'model_class': ChoicesExitType, 'model_name': 'Exit Type', 'template_name': 'setup/generic.html'}, name='choices-exit-type'),
    path('choices_loan_type', views.generic_model_crud, {'model_class': ChoicesLoanType, 'model_name': 'Loan Type', 'template_name': 'setup/generic.html'}, name='choices-loan-type'),
    
]