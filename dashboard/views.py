"""
Views for the Dashboard app.
"""

from datetime import timedelta

from django.db.models import Count, Exists, OuterRef, Sum
from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser, IsOperationsUser
from bl.models import BillOfLading
from bookings.models import Booking, Container
from inventory.models import StockItem
from invoices.models import CommercialInvoice, PackingList
from logistics.pagination import StandardPagination
from proforma.models import ProformaInvoice

from .serializers import CurrentShipmentsSerializer, ProformaStatusSerializer


class KPIView(APIView):
    """
    GET /api/dashboard/kpis/
    Returns key performance indicators computed from current database state.
    Accessible to all authenticated users.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_pis = ProformaInvoice.objects.count()

        pending_payments = ProformaInvoice.objects.filter(
            status=ProformaInvoice.Status.PAYMENT_PENDING
        ).count()

        active_shipments = Booking.objects.exclude(
            status=Booking.Status.COMPLETED
        ).count()

        # Containers in transit: containers on bookings with status
        # between BOOKED and SHIPPED (inclusive of BOOKED, STUFFING, SHIPPED)
        transit_statuses = [
            Booking.Status.BOOKED,
            Booking.Status.STUFFING,
            Booking.Status.SHIPPED,
        ]
        containers_in_transit = Container.objects.filter(
            booking__status__in=transit_statuses
        ).count()

        stock_available = (
            StockItem.objects.aggregate(total=Sum('available_stock'))['total']
            or 0
        )

        return Response({
            'total_pis': total_pis,
            'pending_payments': pending_payments,
            'active_shipments': active_shipments,
            'containers_in_transit': containers_in_transit,
            'stock_available': stock_available,
        })


class ProformaStatusView(ListAPIView):
    """
    GET /api/dashboard/proforma-status/
    Returns a paginated list of non-Paid Proforma Invoices with
    pi_number, customer_name, amount, and status.
    Accessible to all authenticated users.
    """

    serializer_class = ProformaStatusSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return (
            ProformaInvoice.objects.exclude(status=ProformaInvoice.Status.PAID)
            .select_related('customer')
            .order_by('-date', '-pi_number')
        )


class ReadyForBookingView(ListAPIView):
    """
    GET /api/dashboard/ready-for-booking/
    Returns a paginated list of Proforma Invoices with status PAID
    that have no linked Bookings (ready to have a booking created).
    Accessible to Operations and Admin users.
    """

    serializer_class = ProformaStatusSerializer
    permission_classes = [IsOperationsUser | IsAdminUser]
    pagination_class = StandardPagination

    def get_queryset(self):
        return (
            ProformaInvoice.objects.filter(status=ProformaInvoice.Status.PAID)
            .annotate(booking_count=Count('bookings'))
            .filter(booking_count=0)
            .select_related('customer')
            .order_by('-date', '-pi_number')
        )


class CurrentShipmentsView(ListAPIView):
    """
    GET /api/dashboard/current-shipments/
    Returns a paginated list of active Bookings (status != COMPLETED)
    with job_number, customer name, container info, status, ETD, and ETA.
    Accessible to all authenticated users.
    """

    serializer_class = CurrentShipmentsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return (
            Booking.objects.exclude(status=Booking.Status.COMPLETED)
            .select_related('client')
            .prefetch_related('containers')
            .order_by('-etd_pol', '-booking_date')
        )


class DocumentStatusView(APIView):
    """
    GET /api/dashboard/document-status/
    Returns counts of active Bookings with pending documents:
    - invoice_pending: bookings with no finalized CommercialInvoice
    - packing_list_pending: bookings with no finalized PackingList
    - bl_pending: bookings with no released BillOfLading
    Accessible to all authenticated users.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_bookings = Booking.objects.exclude(status=Booking.Status.COMPLETED)

        # Subqueries to check for finalized invoice, finalized packing list, released BL
        has_finalized_invoice = CommercialInvoice.objects.filter(
            booking=OuterRef('pk'),
            status=CommercialInvoice.Status.FINALIZED,
        )
        has_finalized_packing_list = PackingList.objects.filter(
            booking=OuterRef('pk'),
            status=PackingList.Status.FINALIZED,
        )
        has_released_bl = BillOfLading.objects.filter(
            booking=OuterRef('pk'),
            status=BillOfLading.Status.RELEASED,
        )

        invoice_pending = active_bookings.filter(
            ~Exists(has_finalized_invoice)
        ).count()

        packing_list_pending = active_bookings.filter(
            ~Exists(has_finalized_packing_list)
        ).count()

        bl_pending = active_bookings.filter(
            ~Exists(has_released_bl)
        ).count()

        return Response({
            'invoice_pending': invoice_pending,
            'packing_list_pending': packing_list_pending,
            'bl_pending': bl_pending,
        })


class AlertsView(APIView):
    """
    GET /api/dashboard/alerts/
    Returns active alerts grouped by type:
    - payment_overdue: PIs in PAYMENT_PENDING status for more than 30 days
    - shipment_delay: Bookings where ETD has passed but status is not Shipped or Completed
    - missing_bl: Bookings with status SHIPPED that have no linked BillOfLading
    Accessible to all authenticated users.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        threshold_date = now - timedelta(days=30)

        # Payment overdue: PIs in PAYMENT_PENDING where updated_at is older than 30 days
        overdue_pis = ProformaInvoice.objects.filter(
            status=ProformaInvoice.Status.PAYMENT_PENDING,
            updated_at__lte=threshold_date,
        ).select_related('customer')

        payment_overdue = [
            {
                'type': 'payment_overdue',
                'pi_number': pi.pi_number,
                'customer_name': pi.customer.name,
                'amount': str(pi.total_amount),
                'days_overdue': (now - pi.updated_at).days,
                'message': (
                    f"PI {pi.pi_number} for {pi.customer.name} has been in "
                    f"Payment Pending for {(now - pi.updated_at).days} days"
                ),
            }
            for pi in overdue_pis
        ]

        # Shipment delay: Bookings where ETD has passed and status is not Shipped/Completed
        delayed_bookings = Booking.objects.filter(
            etd_pol__lt=now,
        ).exclude(
            status__in=[Booking.Status.SHIPPED, Booking.Status.COMPLETED],
        ).select_related('client')

        shipment_delay = [
            {
                'type': 'shipment_delay',
                'job_number': booking.job_number,
                'customer_name': booking.client.name,
                'etd': booking.etd_pol.isoformat() if booking.etd_pol else None,
                'status': booking.status,
                'message': (
                    f"Booking {booking.job_number} for {booking.client.name} "
                    f"has passed ETD ({booking.etd_pol.strftime('%Y-%m-%d')}) "
                    f"but is still in {booking.get_status_display()} status"
                ),
            }
            for booking in delayed_bookings
        ]

        # Missing BL: Bookings with status SHIPPED that have no linked BillOfLading
        has_bl = BillOfLading.objects.filter(booking=OuterRef('pk'))
        missing_bl_bookings = Booking.objects.filter(
            status=Booking.Status.SHIPPED,
        ).exclude(
            Exists(has_bl),
        ).select_related('client')

        missing_bl = [
            {
                'type': 'missing_bl',
                'job_number': booking.job_number,
                'customer_name': booking.client.name,
                'status': booking.status,
                'message': (
                    f"Booking {booking.job_number} for {booking.client.name} "
                    f"is shipped but has no Bill of Lading"
                ),
            }
            for booking in missing_bl_bookings
        ]

        return Response({
            'payment_overdue': payment_overdue,
            'shipment_delay': shipment_delay,
            'missing_bl': missing_bl,
        })
