from decimal import Decimal
from .models import ContributionRate, TaxBand, CompanyInformation, StaffIncome, StaffDeduction, IncomeType

class PayrollCalculator:
    def __init__(self, staffno, month):
        self.staffno = staffno
        self.month = month

    def get_settings(self):
        return ContributionRate.objects.latest('created')
    
    def get_all_income_type(self):
        return IncomeType.objects.all()

    def get_tax_bands(self):
        return TaxBand.objects.all().order_by('lower_limit')
    
    
    def get_entitled_basic_salary(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        basic_salary = Decimal(company_info.salary) if company_info else Decimal("0.00")
        entitled_basic_salary = Decimal(basic_salary * (company_info.basic_entitled_percentage / 100))
        print("Entitled Basic Salary: ", entitled_basic_salary)
        return round(entitled_basic_salary, 2)
    
    
    def get_allowance_values(self):
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
            percentage_on_basic = Decimal("0.00")
            
            if income.amount:
                entitled = income.amount * (income.income_entitlement / 100)
            elif income.percentage_of_basic:
                percentage_on_basic = Decimal(income.percentage_of_basic)
                base_amount = (percentage_on_basic / 100) * basic_salary
                entitled = base_amount * (income.income_entitlement / 100)
            else:
                entitled = Decimal("0.00")

            entitlement_list.append({
                "income_type": income.income_type,
                "entitled_amount": round(entitled, 2),
                "percentage_on_basic": percentage_on_basic,
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
        # all_income_types = self.get_all_income_type()

        total_tax = Decimal("0.00")
        rent_tax = Decimal("0.00")
        withholding_tax_rate = Decimal("10.00")
        withholding_tax_details = []
        rent_tax_details = None

        for income in income_list:
            income_type = income["income_type"].lower()
            entitled = Decimal(income["entitled_amount"])
            
            # exclude rent, fuel, miscellaneous, and calculate withholding tax on the rest
            if income_type not in ["rent", "fuel", "miscellaneous", "transportation"]:
                tax_amount = entitled * (withholding_tax_rate / 100)
                
                detail = {
                    "income_type": income["income_type"],
                    "entitled_amount": round(entitled, 2),
                    "tax_rate": withholding_tax_rate,
                    "tax_amount": round(tax_amount, 2),
                }
                
                withholding_tax_details.append(detail)
                total_tax += tax_amount

            if income_type == "rent":
                rent_tax_rate = Decimal("8.00")
                tax_amount = entitled * (rent_tax_rate / 100)
                rent_tax_details = {
                    "income_type": income["income_type"],
                    "entitled_amount": round(entitled, 2),
                    "tax_rate": rent_tax_rate,
                    "tax_amount": round(tax_amount, 2),
                }
                rent_tax = tax_amount

        return {
            "total_tax": round(total_tax, 2),
            "rent_tax": round(rent_tax, 2),
            "tax_breakdown": withholding_tax_details,
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
            return {"amount": Decimal("0.00"), "rate": None}
        
        settings = self.get_settings()
        rate = Decimal(settings.employee_pf_rate)
        basic_salary = self.get_entitled_basic_salary()
        
        rent_amount = Decimal("0.00")
        income_list = self.get_allowance_values()["incomes"]
        
        for income in income_list:
            if income["income_type"].lower() == "rent":
                rent_amount += Decimal(income["entitled_amount"])                
                break
            
        total_base = basic_salary + rent_amount
        extimated_pf = total_base * (rate / 100)
        print("PF Value: ", extimated_pf)
        return {"amount": round(extimated_pf, 2), "rate": rate}
    
    
    def get_employer_pf_contribution(self):
        company_info = CompanyInformation.objects.filter(staffno=self.staffno).first()
        if not company_info.pf_con:
            return Decimal("0.00")
        settings = self.get_settings()
        extimated_pf = self.get_entitled_basic_salary() * (Decimal(settings.employer_pf_rate) / 100)
        print("Employer PF Value: ", extimated_pf)
        return round(extimated_pf, 2)


    def get_taxable_income(self):
        taxable_pay = self.get_entitled_basic_salary() + self.get_miscellaneous_and_benefit_in_kind() - self.get_ssnit_contribution()["amount"] - self.get_pf_contribution()["amount"]
        print("Taxable Pay: ", taxable_pay)
        return round(taxable_pay, 2)
        

    def get_income_tax(self):
        income = self.get_taxable_income()  
        print("Taxable Income: ", income)
        total_income_tax = self.calculate_tax(income)
        
        print("Total Income", total_income_tax)
        return {"tax": total_income_tax}


    def get_deductions(self):
        basic_salary = self.get_entitled_basic_salary()
        selected_month = self.month
        
        deductions = StaffDeduction.objects.filter(
            staffno=self.staffno,
            start_month__year__lte=selected_month.year,
            start_month__month__lte=selected_month.month,
            end_month__year__gte=selected_month.year,
            end_month__month__gte=selected_month.month,
        )
        
        deduction_list = []
        total_deduction = Decimal("0.00")
        
        for deduction in deductions:
            percentage_on_basic = Decimal("0.00")
            
            if deduction.amount:
                deductable = deduction.amount
            elif deduction.percentage_of_basic:
                percentage_on_basic = Decimal(deduction.percentage_of_basic)
                base_amount = (percentage_on_basic / 100) * basic_salary
                deductable = base_amount
            else:
                deductable = Decimal("0.00")

            deduction_list.append({
                "deduction_type": deduction.deduction_type,
                "deductable_amount": round(deductable, 2),
                "percentage_on_basic": percentage_on_basic,
            })
            
            total_deduction += deductable
        
        print(f"Staff Deductions: {round(total_deduction, 2)}")
        return {"deductions": deduction_list, "total_deduction": round(total_deduction, 2)}


    def get_total_deductions(self):
        total_deduction = Decimal(self.get_deductions()["total_deduction"])
        sum_of_total_deduction = sum([self.get_ssnit_contribution()["amount"],self.get_tax_for_taxable_income()["rent_tax"],self.get_tax_for_taxable_income()["total_tax"],self.get_pf_contribution()["amount"],Decimal(self.get_income_tax()["tax"]),total_deduction])
        print("Sum of Total Deduction: ", sum_of_total_deduction)
        return round(sum_of_total_deduction, 2)


    def get_net_salary(self):
        return round(self.get_gross_income() - self.get_total_deductions(), 2)

    
    def calculate_tax(self, income):
        bands = TaxBand.objects.order_by("id")
        remaining_income = round(Decimal(income), 2)
        total_tax = Decimal("0.00")

        for band in bands:
            if remaining_income <= 0:
                break

            amount = band.upper_limit if band.upper_limit is not None else remaining_income
            rate = (band.rate or Decimal("0.00")) / 100            
            print("Rate: ", rate)
            taxable_amount = min(remaining_income, amount)
            print("Taxable Amount: ", taxable_amount)
            tax = round(taxable_amount * rate, 2)
            print("Tax on taxable amount: ", tax)
            total_tax += tax
            remaining_income -= taxable_amount
            print("Remaining Income: ", remaining_income)
            print("Total Tax: ", total_tax)

        return round(total_tax, 2)
    
    
    
    def get_benefits_in_kind(self):
        income_list = self.get_allowance_values()["incomes"]
        basic_salary = self.get_entitled_basic_salary()
        miscellaneous_amount = Decimal("0.00")
        has_rent = False
        has_fuel = False
        has_vechile = False
        has_driver = False
        
        benefit_rent_rate = self.get_all_income_type().filter(name__iexact="rent").first().bik_rate or Decimal("7.50")
        benefit_fuel_rate = self.get_all_income_type().filter(name__iexact="fuel").first().bik_rate or Decimal("5.00")
        benefit_vechile_rate = self.get_all_income_type().filter(name__iexact="Official Car Use").first().bik_rate or Decimal("5.00")
        benefit_driver_rate = self.get_all_income_type().filter(name__iexact="Drivers Allowance").first().bik_rate or Decimal("2.50")
        
        print("Benefit in Kind Rates: ", benefit_rent_rate, benefit_fuel_rate, benefit_vechile_rate, benefit_driver_rate)        
        
        for income in income_list:
            income_type = income["income_type"].lower()
            amount = Decimal(income["entitled_amount"])
            
            if income_type == "miscellaneous":
                miscellaneous_amount += amount
            elif income_type == "rent":
                has_rent = True
            elif income_type == "fuel":
                has_fuel = True
            elif income_type == "official car use":
                has_vechile = True
            elif income_type == "drivers allowance":
                has_driver = True
                
        total_cash_enuroment = basic_salary + miscellaneous_amount
        print("Total Cash Enuroment: ", total_cash_enuroment)
        
        rent_bik = Decimal("0.00")
        fuel_bik = Decimal("0.00")
        vechile_bik = Decimal("0.00")
        driver_bik = Decimal("0.00")
        
        
        if has_rent:
            rent_bik = total_cash_enuroment * (benefit_rent_rate / 100)
        if has_fuel:
            fuel_bik = min(total_cash_enuroment * (benefit_fuel_rate / 100), Decimal("625.00"))  
        if has_vechile:
            vechile_bik = min(total_cash_enuroment * (benefit_vechile_rate / 100), Decimal("625.00"))
        if has_driver:
            driver_bik = min(total_cash_enuroment * (benefit_driver_rate / 100), Decimal("250.00"))
                      
        total_bik = rent_bik + fuel_bik + vechile_bik + driver_bik

        benefit_in_kind_list = {
            "rent_bik": round(rent_bik, 2),
            "fuel_bik": round(fuel_bik, 2),
            "vechile_bik": round(vechile_bik, 2),
            "driver_bik": round(driver_bik, 2),
            "total_bik": round(total_bik, 2)
        }

        print("Benefit in Kind:", benefit_in_kind_list)
        return {"benefit_in_kind": benefit_in_kind_list}
    
    
    def get_miscellaneous_and_benefit_in_kind(self):
        income_list = self.get_allowance_values()["incomes"]
        benefit_in_kind = self.get_benefits_in_kind()["benefit_in_kind"]
        miscellaneous = Decimal("0.00")
        
        for income in income_list:
            if income["income_type"].lower() == "miscellaneous":
                miscellaneous = Decimal(income["entitled_amount"])
                break
            
        total_miscellaneous_and_bik = miscellaneous + benefit_in_kind["total_bik"]
        print("Total Miscellaneous and Benefit in Kind: ", total_miscellaneous_and_bik)
        
        return round(total_miscellaneous_and_bik, 2)