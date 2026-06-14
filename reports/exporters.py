"""
Report export utilities for CSV and Excel (xlsx) formats.

Provides reusable export functions that convert querysets into downloadable
HTTP responses. Both formats are capped at 50,000 rows.
"""

import csv
import io
from datetime import date, datetime

from django.http import HttpResponse

MAX_EXPORT_ROWS = 50_000


def _format_value(value):
    """Format a value for export (handle None, datetime, date)."""
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M')
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    return str(value)


def _extract_row(obj, columns):
    """Extract a row of data from an object using column accessors."""
    row = []
    for col in columns:
        accessor = col['accessor']
        value = accessor(obj)
        row.append(_format_value(value))
    return row


def export_to_csv(queryset, columns, filename='report.csv'):
    """
    Export a queryset to CSV format.

    Args:
        queryset: Django queryset (will be sliced to MAX_EXPORT_ROWS).
        columns: List of dicts with 'header' and 'accessor' keys.
            - header: Column display name (str)
            - accessor: Callable that takes an object and returns the value.
        filename: Name of the downloaded file.

    Returns:
        HttpResponse with text/csv content type.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Write header row
    headers = [col['header'] for col in columns]
    writer.writerow(headers)

    # Write data rows (capped)
    for obj in queryset[:MAX_EXPORT_ROWS]:
        writer.writerow(_extract_row(obj, columns))

    return response


def export_to_excel(queryset, columns, filename='report.xlsx'):
    """
    Export a queryset to Excel (xlsx) format using openpyxl.

    Args:
        queryset: Django queryset (will be sliced to MAX_EXPORT_ROWS).
        columns: List of dicts with 'header' and 'accessor' keys.
            - header: Column display name (str)
            - accessor: Callable that takes an object and returns the value.
        filename: Name of the downloaded file.

    Returns:
        HttpResponse with xlsx content type.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = 'Report'

    # Write header row with bold styling
    headers = [col['header'] for col in columns]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Write data rows (capped)
    for obj in queryset[:MAX_EXPORT_ROWS]:
        ws.append(_extract_row(obj, columns))

    # Write to response
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
