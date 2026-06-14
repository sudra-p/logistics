from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import (
    Broker,
    Client,
    Commodity,
    Consignee,
    ContainerType,
    Forwarder,
    MarketingPerson,
    Port,
    Shipper,
    ShippingLine,
    Transporter,
    Vessel,
)


class BaseEntitySerializer(serializers.ModelSerializer):
    """
    Base serializer for all master data entities.
    Enforces:
    - name is required and max 255 characters
    - unique name validation per entity type
    - read-only audit fields (created_at, updated_at)
    """

    class Meta:
        fields = ['id', 'name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_fields(self):
        fields = super().get_fields()
        # Ensure name field has required and non-blank constraints
        if 'name' in fields:
            fields['name'].required = True
            fields['name'].allow_blank = False
            # Replace default UniqueValidator message with entity-specific message
            model = self.Meta.model
            for i, validator in enumerate(fields['name'].validators):
                if isinstance(validator, UniqueValidator):
                    fields['name'].validators[i] = UniqueValidator(
                        queryset=model.objects.all(),
                        message=f"A {model._meta.verbose_name} with this name already exists.",
                    )
                    break
        return fields

    def validate_name(self, value):
        """Validate name field: required, non-blank, max 255 chars."""
        if not value or not value.strip():
            raise serializers.ValidationError("This field may not be blank.")
        if len(value) > 255:
            raise serializers.ValidationError(
                "Ensure this field has no more than 255 characters."
            )
        return value.strip()


class ClientSerializer(BaseEntitySerializer):
    """Serializer for Client entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = Client
        fields = BaseEntitySerializer.Meta.fields + [
            'email',
            'contact_person',
            'phone',
            'address',
        ]

    def validate_contact_person(self, value):
        if value and len(value) > 255:
            raise serializers.ValidationError(
                "Ensure this field has no more than 255 characters."
            )
        return value

    def validate_phone(self, value):
        if value and len(value) > 50:
            raise serializers.ValidationError(
                "Ensure this field has no more than 50 characters."
            )
        return value


class ConsigneeSerializer(BaseEntitySerializer):
    """Serializer for Consignee entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = Consignee
        fields = BaseEntitySerializer.Meta.fields + ['address']


class ShipperSerializer(BaseEntitySerializer):
    """Serializer for Shipper entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = Shipper
        fields = BaseEntitySerializer.Meta.fields + ['address']


class BrokerSerializer(BaseEntitySerializer):
    """Serializer for Broker (CHA) entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = Broker
        fields = BaseEntitySerializer.Meta.fields + ['license_no']

    def validate_license_no(self, value):
        if value and len(value) > 100:
            raise serializers.ValidationError(
                "Ensure this field has no more than 100 characters."
            )
        return value


class ShippingLineSerializer(BaseEntitySerializer):
    """Serializer for Shipping Line entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = ShippingLine
        fields = BaseEntitySerializer.Meta.fields + ['code']

    def validate_code(self, value):
        if value and len(value) > 20:
            raise serializers.ValidationError(
                "Ensure this field has no more than 20 characters."
            )
        return value


class VesselSerializer(BaseEntitySerializer):
    """Serializer for Vessel entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = Vessel
        fields = BaseEntitySerializer.Meta.fields + ['imo_number', 'shipping_line']

    def validate_imo_number(self, value):
        if value and len(value) > 20:
            raise serializers.ValidationError(
                "Ensure this field has no more than 20 characters."
            )
        return value

    def validate_shipping_line(self, value):
        if value and not ShippingLine.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError(
                "Invalid shipping line reference."
            )
        return value


class PortSerializer(BaseEntitySerializer):
    """Serializer for Port entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = Port
        fields = BaseEntitySerializer.Meta.fields + ['code', 'country']

    def validate_code(self, value):
        if value and len(value) > 10:
            raise serializers.ValidationError(
                "Ensure this field has no more than 10 characters."
            )
        return value

    def validate_country(self, value):
        if value and len(value) > 100:
            raise serializers.ValidationError(
                "Ensure this field has no more than 100 characters."
            )
        return value


class CommoditySerializer(BaseEntitySerializer):
    """Serializer for Commodity entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = Commodity
        fields = BaseEntitySerializer.Meta.fields + ['hs_code']

    def validate_hs_code(self, value):
        if value and len(value) > 20:
            raise serializers.ValidationError(
                "Ensure this field has no more than 20 characters."
            )
        return value


class ContainerTypeSerializer(BaseEntitySerializer):
    """Serializer for Container Type entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = ContainerType
        fields = BaseEntitySerializer.Meta.fields + ['code']

    def validate_code(self, value):
        if value and len(value) > 10:
            raise serializers.ValidationError(
                "Ensure this field has no more than 10 characters."
            )
        return value


class MarketingPersonSerializer(BaseEntitySerializer):
    """Serializer for Marketing/Sales Person entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = MarketingPerson
        fields = BaseEntitySerializer.Meta.fields + ['user']


class TransporterSerializer(BaseEntitySerializer):
    """Serializer for Transporter entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = Transporter


class ForwarderSerializer(BaseEntitySerializer):
    """Serializer for Forwarder / Overseas Agent entity."""

    class Meta(BaseEntitySerializer.Meta):
        model = Forwarder
        fields = BaseEntitySerializer.Meta.fields + ['country']

    def validate_country(self, value):
        if value and len(value) > 100:
            raise serializers.ValidationError(
                "Ensure this field has no more than 100 characters."
            )
        return value


# Registry mapping entity type slugs to their serializers
ENTITY_SERIALIZER_MAP = {
    'clients': ClientSerializer,
    'consignees': ConsigneeSerializer,
    'shippers': ShipperSerializer,
    'brokers': BrokerSerializer,
    'shipping-lines': ShippingLineSerializer,
    'vessels': VesselSerializer,
    'ports': PortSerializer,
    'commodities': CommoditySerializer,
    'container-types': ContainerTypeSerializer,
    'marketing-persons': MarketingPersonSerializer,
    'transporters': TransporterSerializer,
    'forwarders': ForwarderSerializer,
}
