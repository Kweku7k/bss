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
    
    
    def get_allowance_values(self):
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
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        basic_salary = Decimal(company_info.salary) if company_info else Decimal("0.00")
        
        total_entitled = Decimal(self.get_allowance_values()["total_entitlement"])
        gross_income = basic_salary + total_entitled
        print("Gross Income: ", gross_income)
        return gross_income
    
 
    def get_tax_for_taxable_income(self):
        income_list = self.get_allowance_values()["incomes"]
        taxable_income_types = {i.name.lower(): i.tax_rate for i in self.get_taxable_income_tax()}

        total_tax = Decimal("0.00")
        tax_details = []

        for income in income_list:
            income_type = income["income_type"].lower()
            entitled = Decimal(income["entitled_amount"])

            if income_type in taxable_income_types:
                tax_rate = taxable_income_types[income_type]
                tax_amount = entitled * (tax_rate / 100)

                tax_details.append({
                    "income_type": income["income_type"],
                    "entitled_amount": round(entitled, 2),
                    "tax_rate": tax_rate,
                    "tax_amount": round(tax_amount, 2),
                })

                total_tax += tax_amount
                
        print("Total Tax", total_tax)

        return {
            "total_tax": round(total_tax, 2),
            "tax_breakdown": tax_details
        }
        
    

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
        income = self.get_taxable_income()  
        print("Taxable Income: ", income)
        total_income_tax = self.calculate_tax(income)
        
        print("Total Income", total_income_tax)
        
        return {"tax": total_income_tax}

        # for band in self.get_tax_bands():
        #     lower = float(band.lower_limit)
        #     upper = float(band.upper_limit) if band.upper_limit else float('inf')  # No upper = open-ended
        #     rate = float(band.rate)

        #     print(f"Checking Band: {lower} - {upper}, Rate: {rate}")

        #     if lower <= taxable <= upper:
        #         tax = round(taxable * (rate / 100), 2)
        #         break

        # print("Taxable Income:", taxable)
        # print("Applied Tax:", tax)

        # return {"tax": round(tax, 2)}

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
        # brackets = [
        #     (Decimal("490.0"), Decimal("0.00")),
        #     (Decimal("110.0"), Decimal("0.05")),
        #     (Decimal("130.0"), Decimal("0.10")),
        #     (Decimal("3166.7"), Decimal("0.175")),
        #     (Decimal("16000.0"), Decimal("0.25")),
        #     (Decimal("30520.0"), Decimal("0.30")),
        #     (Decimal('Infinity'), Decimal("0.35"))
        # ]

        # remaining_income = round(Decimal(income), 1)
        # print("Remaining Income: ", remaining_income)
        # total_tax = Decimal("0.00")

        # for amount, rate in brackets:
        #     if remaining_income <= 0:
        #         break

        #     taxable_amount = min(remaining_income, amount)
        #     tax = round(taxable_amount * rate, 2)
        #     total_tax += tax
        #     remaining_income = round(remaining_income - taxable_amount, 2)

        # return round(total_tax, 2)