DEPENDANTS={
        ('Wife','Wife'),
        ('Husband','Husband'),
        ('Son','Son'),
        ('Daughter','Daughter'),
        ('Father','Father'),
        ('Mother','Mother'),
        ('Self','Self'),
    }
DEPENDANTS = [(key, value) for key, value in DEPENDANTS.items()]

HEQ={
        'None','None',
        'BECE','BECE',
        'WASSCE','WASSCE',
        'Certificate','Certificate',
        'Diploma','Diploma',
        'First Degree','First Degree',
        'MPhil','MPhil',
        'MSc','MSc',
        'MBA','MBA',
        'MA','MA',
        'EMBA','EMBA',
        'PhD','PhD',
        'PGDip','PGDip',
   }
STAFFSTATUS ={
        'Active','Active',
        'Retired','Retired',
        'Suspended','Suspended',
        'Dismissed','Dismissed',
        'Interdicted','Interdicted',
        'Sabbatical','Sabbatical',
        'Inactive','Inactive',
        'Deceased','Deceased',
        'Leave of Absence','Leave of Absence',
        'Leave With Pay','Leave With Pay',
        'Leave Without Pay','Leave Without Pay',
        'Resigned','Resigned',
        'Termination','Resigned',
    }
REGION={
        'GAR','Greater Accra',
        'WR','Western',
        'NR','Northern',
        'ER','Eastern',
        'VR','Volta',
        'OR','Oti',
        'UWR','Upper West',
        'UER','Upper East',
        'NER','North East',
        'BER','Bono East',
        'AS','Ashanti',
        'AR','Ahafo',
        'WNR','Western North',
        'CR','Central',
        'SR','Savannah',
        'BR','Bono',
    }
         
TITLE ={
        'Mr.','Mr.',
        'Mrs.','Mrs.',
        'Dr.','Dr.',
        'Prof.','Prof.',
        'Rev. Dr.','Rev. Dr.',
        'Rev.','Rev.',
        'Ms.','Ms.',
        'Miss.','Miss.',
        'Rev. Prof.','Rev. Prof.',
        'Rev. Mrs.','Rev. Mrs.',
        'Bro.','Bro.',
        'Sis.','Sis.',
        'Fr.','Fr.',
        'Rev Fr.','Rev Fr.',
        'Rev. Sis.','Rev. Sis.',
    }
TITLE = [(key, value) for key, value in TITLE.items()]

SUFFIX ={
        '','None',
        'Jr','Jr',
        'Jnr','Jnr',
        'Snr','Snr',
        'I','I',
        'II','II',
        'III','III',
        'IV','IV',
        'V','V',
        'VI','VI',
        'VII','VII',
        'VIII','VIII',
        'IX','IX',
        'X','X',
    }
TITLE = [(key, value) for key, value in HEQ.items()]

    

STAFFRANK={
        'EXEC','Executive',
        'MGT','Management',
        'SM','Senior Member',
        'SS','Senior Staff',
        'JS','Junior Staff',
        'CAS','Casual Staff',
        'NSP','National Service Person',
        'PNS','Post National Service',
        'PRC','Post Retirement Contract',
        'CS','Contract Staff',
   }

RBA={
        'MGT','Management',
        'HOD','Head of Dept/Directorate',
        'SUP','Unit/Section Head',
        'REG','Regular Staff',
   }

GENDER={
        'M','Male',
        'F','Female',
        'O','Other',
   }
DEPARTMENT={
    'Finance','Finance',
    'HR','HR',
    'IT','IT',
    'GEN. ADMIN','Gen. Admin',
    'Audit','Audit',
}

BRANCH={
    'Osu','Osu',
    'Kaneshie','Kaneshie',
    'Miotso','Miotso',
    'Christ Temple','Christ Temple',
    'Kumasi','Kumasi',
    'Head Office','Head Office',
}
OFFICE={
    'Admissions Office','Admissions Office',
    'Accounts Office','Accounts Office',
    'Dean Office','Dean Office',
    'Dean of Students Office','Dean of Students',
}