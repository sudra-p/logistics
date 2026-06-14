from django.conf import settings
from django.db import models


def generate_job_number():
    """
    Generate a unique sequential job number using a PostgreSQL sequence.
    Falls back to max-based generation for SQLite (test environments).
    """
    from django.db import connection

    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute("SELECT nextval('booking_job_number_seq')")
            seq = cursor.fetchone()[0]
    else:
        # SQLite fallback for tests
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(job_number, 5) AS INTEGER)), 0) + 1 "
                "FROM bookings_booking"
            )
            seq = cursor.fetchone()[0]
    return f"JOB-{seq:06d}"


class Booking(models.Model):
    """Sea export forwarding booking record."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        DO_BOOKING_EDIT = 'DO_BOOKING_EDIT', 'DO-Booking Edit'
        COMPLETED = 'COMPLETED', 'Completed'

    class CargoType(models.TextChoices):
        FCL = 'FCL', 'Full Container Load'
        LCL = 'LCL', 'Less than Container Load'

    class FreightTerms(models.TextChoices):
        PREPAID = 'PREPAID', 'Prepaid'
        COLLECT = 'COLLECT', 'Collect'

    # Auto-generated identifiers
    job_number = models.CharField(max_length=20, unique=True, editable=False)
    booking_no = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    # Dates (mandatory)
    booking_date = models.DateField()
    booking_validity_date = models.DateField()
    forwarding_window_start = models.DateField()
    forwarding_window_end = models.DateField()

    # References (mandatory FK)
    shipping_line = models.ForeignKey(
        'master_data.ShippingLine',
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    pol = models.ForeignKey(
        'master_data.Port',
        on_delete=models.PROTECT,
        related_name='bookings_as_pol',
    )
    pod = models.ForeignKey(
        'master_data.Port',
        on_delete=models.PROTECT,
        related_name='bookings_as_pod',
    )
    client = models.ForeignKey(
        'master_data.Client',
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    commodity = models.ForeignKey(
        'master_data.Commodity',
        on_delete=models.PROTECT,
        related_name='bookings',
    )

    # Classification (mandatory)
    cargo_type = models.CharField(max_length=3, choices=CargoType.choices)
    shipment_type = models.CharField(max_length=50)
    stuffing_type = models.CharField(max_length=50)

    # Optional references
    vessel = models.ForeignKey(
        'master_data.Vessel',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings',
    )
    por = models.ForeignKey(
        'master_data.Port',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings_as_por',
    )
    fpd = models.ForeignKey(
        'master_data.Port',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings_as_fpd',
    )
    transporter = models.ForeignKey(
        'master_data.Transporter',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings',
    )
    marketing_person = models.ForeignKey(
        'master_data.MarketingPerson',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings',
    )
    nvocc_forwarder = models.ForeignKey(
        'master_data.Forwarder',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings',
    )
    shipper = models.ForeignKey(
        'master_data.Shipper',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings',
    )
    consignee = models.ForeignKey(
        'master_data.Consignee',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings',
    )

    # Voyage and schedule
    voyage = models.CharField(max_length=100, blank=True)
    etd_pol = models.DateTimeField(null=True, blank=True)
    eta_destination = models.DateTimeField(null=True, blank=True)

    # Cut-off dates
    si_cut_off = models.DateTimeField(null=True, blank=True)
    vgm_cut_off = models.DateTimeField(null=True, blank=True)
    sb_cut_off = models.DateTimeField(null=True, blank=True)
    gate_cut_off = models.DateTimeField(null=True, blank=True)

    # Clearance and stuffing
    clearance_point = models.CharField(max_length=255, blank=True)
    stuffing_point = models.CharField(max_length=255, blank=True)
    expected_stuffing_date = models.DateField(null=True, blank=True)
    is_icd_hand_over = models.BooleanField(default=False)
    transport_involved = models.BooleanField(default=False)
    clearance_involved = models.BooleanField(default=False)

    # Parties
    buyer = models.CharField(max_length=255, blank=True)

    # Documentation
    quotation_no = models.CharField(max_length=50, blank=True)
    docs_holder = models.CharField(max_length=255, blank=True)
    po_no = models.CharField(max_length=100, blank=True)
    shipper_invoice_no = models.CharField(max_length=100, blank=True)
    hbl_no = models.CharField(max_length=50, blank=True)
    mbl_no = models.CharField(max_length=50, blank=True)
    hbl_freight_terms = models.CharField(
        max_length=10, choices=FreightTerms.choices, blank=True
    )
    mbl_freight_terms = models.CharField(
        max_length=10, choices=FreightTerms.choices, blank=True
    )
    bl_type = models.CharField(max_length=50, blank=True)
    mbl_type = models.CharField(max_length=50, blank=True)

    # Certificates (up to 5)
    certificates = models.JSONField(default=list, blank=True)

    # HAZ details (conditional on is_haz)
    is_haz = models.BooleanField(default=False)
    haz_class = models.CharField(max_length=50, blank=True)
    haz_uin = models.CharField(max_length=100, blank=True)
    haz_group = models.CharField(max_length=50, blank=True)

    # Other
    remarks = models.TextField(max_length=2000, blank=True)

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bookings_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings_updated',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-booking_date']
        indexes = [
            models.Index(fields=['booking_date'], name='idx_booking_date'),
            models.Index(fields=['status'], name='idx_status'),
            models.Index(fields=['client'], name='idx_client'),
            models.Index(fields=['shipping_line'], name='idx_shipping_line'),
            models.Index(fields=['etd_pol'], name='idx_etd_pol'),
            models.Index(fields=['job_number'], name='idx_job_number'),
            models.Index(fields=['booking_no'], name='idx_booking_no'),
            models.Index(fields=['hbl_no'], name='idx_hbl_no'),
            models.Index(fields=['mbl_no'], name='idx_mbl_no'),
        ]

    def __str__(self):
        return f"{self.job_number} - {self.client}"

    def save(self, *args, **kwargs):
        if not self.job_number:
            self.job_number = generate_job_number()
        super().save(*args, **kwargs)


class Container(models.Model):
    """Container allocation within a booking."""

    class Size(models.TextChoices):
        FT_20 = '20FT', '20ft'
        FT_40 = '40FT', '40ft'
        FT_40_HC = '40FT_HC', '40ft HC'
        FT_45 = '45FT', '45ft'

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name='containers'
    )
    container_type = models.ForeignKey(
        'master_data.ContainerType',
        on_delete=models.PROTECT,
        related_name='containers',
    )
    container_size = models.CharField(max_length=10, choices=Size.choices)
    container_count = models.PositiveIntegerField()
    container_no = models.CharField(max_length=20, blank=True)
    seal_no = models.CharField(max_length=20, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(container_count__gte=1),
                name='container_count_positive',
            )
        ]

    def __str__(self):
        return f"{self.container_size} x{self.container_count} ({self.booking.job_number})"


class TranshipmentLeg(models.Model):
    """Transhipment routing leg for multi-port shipments."""

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name='transhipment_legs'
    )
    sequence = models.PositiveSmallIntegerField()  # 1-4
    port = models.ForeignKey(
        'master_data.Port',
        on_delete=models.PROTECT,
        related_name='transhipment_legs',
    )
    eta = models.DateTimeField()
    connecting_vessel_voyage = models.CharField(max_length=200)
    etd = models.DateTimeField()

    class Meta:
        ordering = ['sequence']
        unique_together = ['booking', 'sequence']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(sequence__lte=4),
                name='max_four_legs',
            ),
            models.CheckConstraint(
                condition=models.Q(etd__gt=models.F('eta')),
                name='etd_after_eta',
            ),
        ]

    def __str__(self):
        return f"Leg {self.sequence}: {self.port} ({self.booking.job_number})"


class BookingStatusHistory(models.Model):
    """Audit trail for booking status transitions."""

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name='status_history'
    )
    previous_status = models.CharField(
        max_length=20, choices=Booking.Status.choices
    )
    new_status = models.CharField(
        max_length=20, choices=Booking.Status.choices
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.booking.job_number}: {self.previous_status} → {self.new_status}"


class CommunicationLog(models.Model):
    """Log of emails sent for a booking."""

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name='communication_logs'
    )
    email_type = models.CharField(max_length=50)
    recipients = models.JSONField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email_type} - {self.status} ({self.booking.job_number})"
