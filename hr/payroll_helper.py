# payroll_utils.py (your helper file)

from decimal import Decimal
from .models import ContributionRate, TaxBand, CompanyInformation, StaffIncome, StaffDeduction, IncomeType

class PayrollCalculator:
    def __init__(self, staffno, month):
        self.staffno = staffno
        self.month = month

    def get_settings(self):
        return ContributionRate.objects.latest('created')
    
    def get_taxable_income_tax(self):
        return IncomeType.objects.filter(taxable=True)

    def get_tax_bands(self):
        return TaxBand.objects.all().order_by('lower_limit')
    
    
    def get_entitled_basic_salary(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        basic_salary = Decimal(company_info.salary) if company_info else Decimal("0.00")
        entitled_basic_salary = Decimal(basic_salary * (company_info.basic_entitled_percentage / 100))
        print("Etitled Basic Salary: ", entitled_basic_salary)
        return entitled_basic_salary
    
    
    def get_allowance_values(self):
        # company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        # basic_salary = Decimal(company_info.salary) if company_info else Decimal("0.00")
        basic_salary = self.get_entitled_basic_salary()
        selected_month = self.month

        incomes = StaffIncome.objects.filter(
            staffno=self.staffno,
            start_month__year__lte=selected_month.year,
            start_month__month__lte=selected_month.month,
            end_month__year__gte=selected_month.year,
            end_month__month__gte=selected_month.month,
        )

        entitlement_list = []
        total_entitled = Decimal("0.00")

        for income in incomes:
            if income.amount:
                entitled = income.amount * (income.income_entitlement / 100)
            elif income.percentage_of_basic:
                base_amount = (income.percentage_of_basic / 100) * basic_salary
                entitled = base_amount * (income.income_entitlement / 100)
            else:
                entitled = Decimal("0.00")

            entitlement_list.append({
                "income_type": income.income_type,
                "entitled_amount": round(entitled, 2),
            })
            
            total_entitled += entitled

            # print(f"{income.income_type} - Entitled: {entitled}")

        print(f"Total Entitlement: {round(total_entitled, 2)}")
        return {"incomes": entitlement_list, "total_entitlement": round(total_entitled, 2)}
        
        

    def get_gross_income(self):
        basic_salary = self.get_entitled_basic_salary()
        
        total_entitled = Decimal(self.get_allowance_values()["total_entitlement"])
        gross_income = basic_salary + total_entitled
        print("Gross Income: ", gross_income)
        return gross_income
    
    
    
    def get_tax_for_taxable_income(self):
        income_list = self.get_allowance_values()["incomes"]
        taxable_income_types = {i.name.lower(): i.tax_rate for i in self.get_taxable_income_tax()}

        total_tax = Decimal("0.00")
        rent_tax = Decimal("0.00")
        tax_details = []
        rent_tax_details = None

        for income in income_list:
            income_type = income["income_type"].lower()
            entitled = Decimal(income["entitled_amount"])

            if income_type in taxable_income_types:
                tax_rate = taxable_income_types[income_type]
                tax_amount = entitled * (tax_rate / 100)

                detail = {
                    "income_type": income["income_type"],
                    "entitled_amount": round(entitled, 2),
                    "tax_rate": tax_rate,
                    "tax_amount": round(tax_amount, 2),
                }

                if income_type == "rent":
                    rent_tax += tax_amount
                    rent_tax_details = detail
                else:
                    tax_details.append(detail)
                    total_tax += tax_amount

        return {
            "total_tax": round(total_tax, 2),
            "rent_tax": round(rent_tax, 2),
            "tax_breakdown": tax_details,
            "rent_tax_detail": rent_tax_details,
        }
    

    def get_ssnit_contribution(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        if not company_info.ssn_con:
            return {"amount": Decimal("0.00"), "rate": None}
        settings = self.get_settings()
        rate = Decimal(settings.employee_ssnit_rate)
        extimated_ssnit = self.get_entitled_basic_salary() * (rate / 100)
        print("SSNIT Value: ", extimated_ssnit)
        return {"amount": round(extimated_ssnit, 2), "rate": rate}
    
    
    def get_employer_ssnit_contribution(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        if not company_info.ssn_con:
            return Decimal("0.00")
        settings = self.get_settings()
        extimated_ssnit = self.get_entitled_basic_salary() * (Decimal(settings.employer_ssnit_rate) / 100)
        print("Employer SSNIT Value: ", extimated_ssnit)
        return round(extimated_ssnit, 2)
        

    def get_pf_contribution(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        if not company_info.pf_con:
            return Decimal("0.00")
        settings = self.get_settings()
        extimated_pf = self.get_entitled_basic_salary() * (Decimal(settings.employee_pf_rate) / 100)
        print("PF Value: ", extimated_pf)
        return round(extimated_pf, 2)
    
    
    def get_employer_pf_contribution(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        if not company_info.pf_con:
            return Decimal("0.00")
        settings = self.get_settings()
        extimated_pf = self.get_entitled_basic_salary() * (Decimal(settings.employer_pf_rate) / 100)
        print("Employer PF Value: ", extimated_pf)
        return round(extimated_pf, 2)

    def get_taxable_income(self):
        return self.get_gross_income() - self.get_ssnit_contribution()["amount"]

    def get_income_tax(self):
        income = self.get_taxable_income()  
        print("Taxable Income: ", income)
        total_income_tax = self.calculate_tax(income)
        
        print("Total Income", total_income_tax)
        return {"tax": total_income_tax}


    def get_total_deductions(self):
        basic_salary = self.get_entitled_basic_salary()
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
        sum_of_total_deduction = sum([self.get_ssnit_contribution()["amount"],self.get_tax_for_taxable_income()["total_tax"],self.get_pf_contribution(),Decimal(self.get_income_tax()["tax"]),total_deduction])
        print("Sum of Total Deduction: ", sum_of_total_deduction)
        return round(sum_of_total_deduction, 2)

    def get_net_salary(self):
        return round(self.get_gross_income() - self.get_total_deductions(), 2)

    
    def calculate_tax(self, income):
        bands = TaxBand.objects.order_by("id")
        remaining_income = round(Decimal(income), 1)
        total_tax = Decimal("0.00")

        for band in bands:
            if remaining_income <= 0:
                break

            amount = band.upper_limit if band.upper_limit is not None else remaining_income
            rate = (band.rate or Decimal("0.00")) / 100            
            print("Rate: ", rate)
            taxable_amount = min(remaining_income, amount)
            print("Taxable Amount: ", taxable_amount)
            tax = round(taxable_amount * rate, 1)
            print("Tax on taxable amount: ", tax)
            total_tax += tax
            remaining_income -= taxable_amount
            print("Remaining Income: ", remaining_income)
            print("Total Tax: ", total_tax)

        return round(total_tax, 2)