from django.conf import settings
from django.db import models


class BaseEntity(models.Model):
    """
    Abstract base model for all master data entities.
    Provides common fields: name, is_active, created_at, updated_at.
    """

    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        return self.name


class Client(BaseEntity):
    """Client / Customer entity."""

    email = models.EmailField(blank=True, null=True)
    contact_person = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    class Meta(BaseEntity.Meta):
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'


class Consignee(BaseEntity):
    """Consignee entity."""

    address = models.TextField(blank=True)

    class Meta(BaseEntity.Meta):
        verbose_name = 'Consignee'
        verbose_name_plural = 'Consignees'


class Shipper(BaseEntity):
    """Shipper entity."""

    address = models.TextField(blank=True)

    class Meta(BaseEntity.Meta):
        verbose_name = 'Shipper'
        verbose_name_plural = 'Shippers'


class Broker(BaseEntity):
    """CHA/Broker entity."""

    license_no = models.CharField(max_length=100, blank=True)

    class Meta(BaseEntity.Meta):
        verbose_name = 'Broker'
        verbose_name_plural = 'Brokers'


class ShippingLine(BaseEntity):
    """Shipping Line entity."""

    code = models.CharField(max_length=20, blank=True)

    class Meta(BaseEntity.Meta):
        verbose_name = 'Shipping Line'
        verbose_name_plural = 'Shipping Lines'


class Vessel(BaseEntity):
    """Vessel entity."""

    imo_number = models.CharField(max_length=20, blank=True)
    shipping_line = models.ForeignKey(
        ShippingLine,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='vessels',
    )

    class Meta(BaseEntity.Meta):
        verbose_name = 'Vessel'
        verbose_name_plural = 'Vessels'


class Port(BaseEntity):
    """Port entity."""

    code = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=100, blank=True)

    class Meta(BaseEntity.Meta):
        verbose_name = 'Port'
        verbose_name_plural = 'Ports'


class Commodity(BaseEntity):
    """Commodity entity."""

    hs_code = models.CharField(max_length=20, blank=True)

    class Meta(BaseEntity.Meta):
        verbose_name = 'Commodity'
        verbose_name_plural = 'Commodities'


class ContainerType(BaseEntity):
    """Container Type entity."""

    code = models.CharField(max_length=10, blank=True)

    class Meta(BaseEntity.Meta):
        verbose_name = 'Container Type'
        verbose_name_plural = 'Container Types'


class MarketingPerson(BaseEntity):
    """Marketing/Sales Person entity."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marketing_person_profile',
    )

    class Meta(BaseEntity.Meta):
        verbose_name = 'Marketing Person'
        verbose_name_plural = 'Marketing Persons'


class Transporter(BaseEntity):
    """Transporter entity."""

    class Meta(BaseEntity.Meta):
        verbose_name = 'Transporter'
        verbose_name_plural = 'Transporters'


class Forwarder(BaseEntity):
    """Forwarder / Overseas Agent entity."""

    country = models.CharField(max_length=100, blank=True)

    class Meta(BaseEntity.Meta):
        verbose_name = 'Forwarder'
        verbose_name_plural = 'Forwarders'
