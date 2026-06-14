from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import CanModifyBooking
from reports.exporters import export_to_csv, export_to_excel
from reports.generators import ReportGenerator
from reports.serializers import MasterReportSerializer, PendingDOReportSerializer


class ReportPagination(PageNumberPagination):
    """Pagination for report views - max 50 per page."""

    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 50


def _get_pending_do_filters(request):
    """Extract Pending DO report filters from request query params."""
    filters = {}

    client = request.query_params.get('client')
    if client:
        filters['client'] = client

    vessel_voyage = request.query_params.get('vessel_voyage')
    if vessel_voyage:
        filters['vessel_voyage'] = vessel_voyage

    booking_date_from = request.query_params.get('booking_date_from')
    if booking_date_from:
        filters['booking_date_from'] = booking_date_from

    booking_date_to = request.query_params.get('booking_date_to')
    if booking_date_to:
        filters['booking_date_to'] = booking_date_to

    shipping_line = request.query_params.get('shipping_line')
    if shipping_line:
        filters['shipping_line'] = shipping_line

    return filters


def _get_master_filters(request):
    """Extract Master report filters from request query params."""
    filters = {}

    client = request.query_params.get('client')
    if client:
        filters['client'] = client

    vessel_voyage = request.query_params.get('vessel_voyage')
    if vessel_voyage:
        filters['vessel_voyage'] = vessel_voyage

    created_date_from = request.query_params.get('created_date_from')
    if created_date_from:
        filters['created_date_from'] = created_date_from

    created_date_to = request.query_params.get('created_date_to')
    if created_date_to:
        filters['created_date_to'] = created_date_to

    status_filter = request.query_params.get('status')
    if status_filter:
        filters['status'] = status_filter

    shipping_line = request.query_params.get('shipping_line')
    if shipping_line:
        filters['shipping_line'] = shipping_line

    return filters


# Column definitions for export reports

PENDING_DO_COLUMNS = [
    {'header': 'Booking Reference', 'accessor': lambda obj: obj.job_number},
    {'header': 'Client Name', 'accessor': lambda obj: obj.client.name if obj.client else ''},
    {
        'header': 'Vessel/Voyage',
        'accessor': lambda obj: ' / '.join(
            filter(None, [obj.vessel.name if obj.vessel else None, obj.voyage or None])
        ),
    },
    {'header': 'POL', 'accessor': lambda obj: obj.pol.name if obj.pol else ''},
    {'header': 'POD', 'accessor': lambda obj: obj.pod.name if obj.pod else ''},
    {'header': 'ETD', 'accessor': lambda obj: obj.etd_pol},
    {'header': 'ETA', 'accessor': lambda obj: obj.eta_destination},
    {'header': 'Status', 'accessor': lambda obj: obj.get_status_display()},
    {'header': 'Shipping Line', 'accessor': lambda obj: obj.shipping_line.name if obj.shipping_line else ''},
    {'header': 'Container Count', 'accessor': lambda obj: getattr(obj, 'total_container_count', 0) or 0},
    {'header': 'Booking Date', 'accessor': lambda obj: obj.booking_date},
]

MASTER_COLUMNS = [
    {'header': 'Booking Reference', 'accessor': lambda obj: obj.job_number},
    {'header': 'Client Name', 'accessor': lambda obj: obj.client.name if obj.client else ''},
    {
        'header': 'Vessel/Voyage',
        'accessor': lambda obj: ' / '.join(
            filter(None, [obj.vessel.name if obj.vessel else None, obj.voyage or None])
        ),
    },
    {'header': 'POL', 'accessor': lambda obj: obj.pol.name if obj.pol else ''},
    {'header': 'POD', 'accessor': lambda obj: obj.pod.name if obj.pod else ''},
    {'header': 'ETD', 'accessor': lambda obj: obj.etd_pol},
    {'header': 'ETA', 'accessor': lambda obj: obj.eta_destination},
    {'header': 'Status', 'accessor': lambda obj: obj.get_status_display()},
    {'header': 'Shipping Line', 'accessor': lambda obj: obj.shipping_line.name if obj.shipping_line else ''},
    {'header': 'Container Count', 'accessor': lambda obj: getattr(obj, 'total_container_count', 0) or 0},
    {'header': 'Created Date', 'accessor': lambda obj: obj.created_at},
]


class PendingDOReportView(ListAPIView):
    """
    GET /api/reports/pending-do/

    Returns bookings with status Pending or DO-Booking Edit.
    Supports filtering by client, vessel_voyage, booking_date_from,
    booking_date_to, and shipping_line query parameters.

    Paginated with max 50 results per page.
    Accessible by Operations and Admin users.
    """

    serializer_class = PendingDOReportSerializer
    permission_classes = [CanModifyBooking]
    pagination_class = ReportPagination

    def get_queryset(self):
        filters = _get_pending_do_filters(self.request)
        return ReportGenerator.pending_do_report(filters)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if not queryset.exists():
            return Response(
                {'results': [], 'message': 'No pending DO bookings found.'}
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class MasterReportView(ListAPIView):
    """
    GET /api/reports/master/

    Returns all bookings regardless of status.
    Supports filtering by client, vessel_voyage, created_date_from,
    created_date_to, status, and shipping_line query parameters.

    Defaults to last 90 days if no date range specified.
    Sorted by created date descending.
    Paginated with max 50 results per page.
    Accessible by Operations and Admin users.
    """

    serializer_class = MasterReportSerializer
    permission_classes = [CanModifyBooking]
    pagination_class = ReportPagination

    def get_queryset(self):
        filters = _get_master_filters(self.request)
        return ReportGenerator.master_report(filters)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if not queryset.exists():
            return Response(
                {'results': [], 'message': 'No bookings found.'}
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class PendingDOExportView(APIView):
    """
    GET /api/reports/pending-do/export/?format=csv|excel

    Exports the Pending DO report as a downloadable CSV or Excel file.
    Uses the same queryset and filters as the on-screen Pending DO report.
    Capped at 50,000 rows.
    Accessible by Operations and Admin users.
    """

    permission_classes = [CanModifyBooking]

    def get(self, request):
        export_format = request.query_params.get('format')
        if export_format not in ('csv', 'excel'):
            return Response(
                {'error': 'format query parameter is required. Use "csv" or "excel".'},
                status=400,
            )

        filters = _get_pending_do_filters(request)
        queryset = ReportGenerator.pending_do_report(filters)

        if export_format == 'csv':
            return export_to_csv(
                queryset, PENDING_DO_COLUMNS, filename='pending_do_report.csv'
            )
        else:
            return export_to_excel(
                queryset, PENDING_DO_COLUMNS, filename='pending_do_report.xlsx'
            )


class MasterExportView(APIView):
    """
    GET /api/reports/master/export/?format=csv|excel

    Exports the Master report as a downloadable CSV or Excel file.
    Uses the same queryset and filters as the on-screen Master report.
    Capped at 50,000 rows.
    Accessible by Operations and Admin users.
    """

    permission_classes = [CanModifyBooking]

    def get(self, request):
        export_format = request.query_params.get('format')
        if export_format not in ('csv', 'excel'):
            return Response(
                {'error': 'format query parameter is required. Use "csv" or "excel".'},
                status=400,
            )

        filters = _get_master_filters(request)
        queryset = ReportGenerator.master_report(filters)

        if export_format == 'csv':
            return export_to_csv(
                queryset, MASTER_COLUMNS, filename='master_report.csv'
            )
        else:
            return export_to_excel(
                queryset, MASTER_COLUMNS, filename='master_report.xlsx'
            )
