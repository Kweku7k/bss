# utils/export.py
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
import openpyxl

def render_to_pdf(template_path, context, filename="report.pdf"):
    html = render_to_string(template_path, context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

    if pdf.err:
        return HttpResponse("Error rendering PDF", status=500)

    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def render_to_excel(data_dict, filename="report.xlsx"):
    wb = openpyxl.Workbook()
    for sheet_name, rows in data_dict.items():
        ws = wb.create_sheet(title=sheet_name)
        if rows:
            headers = list(rows[0].keys())
            ws.append(headers)
            for row in rows:
                ws.append(list(row.values()))
    
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])

    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    response = HttpResponse(
        file_stream.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
