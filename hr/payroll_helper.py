# payroll_utils.py (your helper file)

from decimal import Decimal
from .models import ContributionRate, TaxBand, CompanyInformation, StaffIncome, StaffDeduction

class PayrollCalculator:
    def __init__(self, staffno, month):
        self.staffno = staffno
        self.month = month

    def get_settings(self):
        return ContributionRate.objects.latest('created')

    def get_tax_bands(self):
        return TaxBand.objects.all().order_by('lower_limit')

    def get_gross_income(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        basic_salary = Decimal(company_info.salary) if company_info else Decimal("0.00")
        selected_month = self.month

        incomes = StaffIncome.objects.filter(
            staffno=self.staffno,
            start_month__year__lte=selected_month.year,
            start_month__month__lte=selected_month.month,
            end_month__year__gte=selected_month.year,
            end_month__month__gte=selected_month.month,
        )

        total_income = Decimal("0.00")
        for i in incomes:
            if i.amount:
                total_income += Decimal(i.amount)
            elif i.percentage_of_basic:
                total_income += (Decimal(i.percentage_of_basic) / 100) * basic_salary

        return total_income + basic_salary

    def get_ssnit_contribution(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        if not company_info.ssn_con:
            return {"amount": Decimal("0.00"), "rate": None}
        settings = self.get_settings()
        rate = Decimal(settings.employee_ssnit_rate)
        extimated_ssnit = Decimal(company_info.salary) * (rate / 100)
        print("SSNIT Value: ", extimated_ssnit)
        return {"amount": round(extimated_ssnit, 2), "rate": rate}
    
    
    def get_employer_ssnit_contribution(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        if not company_info.ssn_con:
            return Decimal("0.00")
        settings = self.get_settings()
        extimated_ssnit = Decimal(company_info.salary) * (Decimal(settings.employer_ssnit_rate) / 100)
        print("Employer SSNIT Value: ", extimated_ssnit)
        return round(extimated_ssnit, 2)
        

    def get_pf_contribution(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        if not company_info.pf_con:
            return Decimal("0.00")
        settings = self.get_settings()
        extimated_pf = Decimal(company_info.salary) * (Decimal(settings.employee_pf_rate) / 100)
        print("PF Value: ", extimated_pf)
        return round(extimated_pf, 2)
    
    
    def get_employer_pf_contribution(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        if not company_info.pf_con:
            return Decimal("0.00")
        settings = self.get_settings()
        extimated_pf = Decimal(company_info.salary) * (Decimal(settings.employer_pf_rate) / 100)
        print("Employer PF Value: ", extimated_pf)
        return round(extimated_pf, 2)

    def get_taxable_income(self):
        return self.get_gross_income() - self.get_ssnit_contribution()["amount"]

    def get_income_tax(self):
        taxable = float(self.get_taxable_income())
        tax = 0.0        

        for band in self.get_tax_bands():
            lower = float(band.lower_limit)
            upper = float(band.upper_limit) if band.upper_limit else float('inf')  # No upper = open-ended
            rate = float(band.rate)

            print(f"Checking Band: {lower} - {upper}, Rate: {rate}")

            if lower <= taxable <= upper:
                tax = round(taxable * (rate / 100), 2)
                break

        print("Taxable Income:", taxable)
        print("Applied Tax:", tax)

        return {"tax": round(tax, 2)}

    def get_total_deductions(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        basic_salary = Decimal(company_info.salary) if company_info else Decimal("0.00")
        selected_month = self.month
        
        deductions = StaffDeduction.objects.filter(
            staffno=self.staffno,
            start_month__year__lte=selected_month.year,
            start_month__month__lte=selected_month.month,
            end_month__year__gte=selected_month.year,
            end_month__month__gte=selected_month.month,
        )
        
        print("Staff Deductions: ", deductions)
        
        total_deduction = Decimal("0.00")
        for d in deductions:
            if d.amount:
                total_deduction += round(Decimal(d.amount), 2)
            elif d.percentage_of_basic:
                total_deduction += round((Decimal(d.percentage_of_basic) / 100) * basic_salary, 2)

        
        print("Total Deductions: ", total_deduction)
        sum_of_total_deduction = sum([self.get_ssnit_contribution()["amount"],self.get_pf_contribution(),Decimal(self.get_income_tax()["tax"]),total_deduction])
        print("Sum of Total Deduction: ", sum_of_total_deduction)
        return round(sum_of_total_deduction, 2)

    def get_net_salary(self):
        return round(self.get_gross_income() - self.get_total_deductions(), 2)
