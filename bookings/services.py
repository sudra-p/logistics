"""
Business logic service layer for Booking operations.
"""

from django.shortcuts import get_object_or_404
from rest_framework import serializers

from bookings.models import Booking, BookingStatusHistory, Container, TranshipmentLeg
from bookings.validators import (
    MAX_TRANSHIPMENT_LEGS,
    validate_transhipment_legs,
    validate_transhipment_legs_chronology,
)


class BookingService:
    """
    Service class encapsulating booking business logic.

    Job number generation is handled by the Booking model's save() method,
    which calls generate_job_number() using a PostgreSQL sequence.
    This ensures job numbers are only consumed on successful save (after validation).
    """

    @staticmethod
    def create_booking(data, user):
        """
        Create a new booking from validated data.

        Args:
            data: Dict of validated booking fields (from BookingCreateSerializer).
            user: The authenticated user creating the booking.

        Returns:
            The created Booking instance with a generated job_number.
        """
        booking = Booking(
            status=Booking.Status.PENDING,
            created_by=user,
            **data,
        )
        booking.save()

        # Queue booking confirmation email (fire-and-forget, don't block creation)
        try:
            from notifications.tasks import send_booking_confirmation_task
            send_booking_confirmation_task.delay(booking.id)
        except Exception:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                'Failed to queue booking confirmation email for booking %s',
                booking.id,
            )

        return booking

    @staticmethod
    def update_booking(booking_id, data, user):
        """
        Update an existing booking with validated data.

        Args:
            booking_id: ID of the booking to update.
            data: Dict of validated fields (from BookingUpdateSerializer).
            user: The authenticated user performing the update.

        Returns:
            The updated Booking instance.

        Raises:
            Http404 if booking not found.
            serializers.ValidationError if booking is completed.
        """
        booking = get_object_or_404(Booking, pk=booking_id)

        if booking.status == Booking.Status.COMPLETED:
            raise serializers.ValidationError(
                {'detail': 'Cannot update a finalized (Completed) booking.'}
            )

        # Apply validated fields to the booking instance
        for field, value in data.items():
            setattr(booking, field, value)

        booking.updated_by = user
        booking.save()
        return booking

    @staticmethod
    def add_containers(booking_id, containers_data, user):
        """
        Add container entries to a booking.

        Args:
            booking_id: ID of the booking to add containers to.
            containers_data: List of validated container dicts
                (container_type, container_size, container_count, container_no, seal_no).
            user: The authenticated user performing the action.

        Returns:
            List of created Container instances.

        Raises:
            Http404 if booking not found.
            serializers.ValidationError if max 50 containers exceeded.
        """
        booking = get_object_or_404(Booking, pk=booking_id)

        existing_count = booking.containers.count()
        new_count = len(containers_data)

        if existing_count + new_count > 50:
            raise serializers.ValidationError({
                'containers': [
                    f'Cannot add {new_count} container(s). '
                    f'Booking already has {existing_count} container(s) '
                    f'and the maximum is 50.'
                ]
            })

        created_containers = []
        for entry in containers_data:
            container = Container(
                booking=booking,
                container_type=entry['container_type'],
                container_size=entry['container_size'],
                container_count=entry['container_count'],
                container_no=entry.get('container_no', ''),
                seal_no=entry.get('seal_no', ''),
            )
            container.save()
            created_containers.append(container)

        return created_containers

    @staticmethod
    def remove_container(booking_id, container_id, user):
        """
        Remove a container entry from a booking.

        Args:
            booking_id: ID of the booking.
            container_id: ID of the container to remove.
            user: The authenticated user performing the action.

        Raises:
            Http404 if booking or container not found.
        """
        booking = get_object_or_404(Booking, pk=booking_id)
        container = get_object_or_404(Container, pk=container_id, booking=booking)
        container.delete()

    @staticmethod
    def add_transhipments(booking_id, legs_data, user):
        """
        Add transhipment legs to a booking.

        Args:
            booking_id: ID of the booking to add legs to.
            legs_data: List of validated leg dicts (port, eta, etd, connecting_vessel_voyage).
            user: The authenticated user performing the action.

        Returns:
            List of created TranshipmentLeg instances.

        Raises:
            Http404 if booking not found.
            serializers.ValidationError if validation fails.
        """
        booking = get_object_or_404(Booking, pk=booking_id)

        existing_legs = booking.transhipment_legs.all()
        existing_count = existing_legs.count()

        # Validate the new legs (checks max count, required fields, ports, ETD>ETA, chronology)
        validate_transhipment_legs(legs_data, existing_legs_count=existing_count)

        # If there are existing legs, validate chronological ordering across all legs
        if existing_count > 0:
            last_existing_leg = existing_legs.order_by('-sequence').first()
            first_new_eta = legs_data[0].get('eta')
            if last_existing_leg and first_new_eta:
                if first_new_eta < last_existing_leg.etd:
                    raise serializers.ValidationError({
                        'legs[0].eta': [
                            'ETA of this leg must be on or after the ETD of the preceding leg.'
                        ]
                    })

        # Assign sequence numbers continuing from existing
        start_sequence = existing_count + 1
        created_legs = []

        for i, leg_data in enumerate(legs_data):
            leg = TranshipmentLeg(
                booking=booking,
                sequence=start_sequence + i,
                port=leg_data['port'],
                eta=leg_data['eta'],
                connecting_vessel_voyage=leg_data['connecting_vessel_voyage'],
                etd=leg_data['etd'],
            )
            leg.save()
            created_legs.append(leg)

        return created_legs

    @staticmethod
    def update_transhipment(booking_id, leg_id, data, user):
        """
        Update a single transhipment leg.

        Args:
            booking_id: ID of the booking.
            leg_id: ID of the transhipment leg to update.
            data: Dict of validated fields to update.
            user: The authenticated user performing the action.

        Returns:
            The updated TranshipmentLeg instance.

        Raises:
            Http404 if booking or leg not found.
            serializers.ValidationError if validation fails.
        """
        booking = get_object_or_404(Booking, pk=booking_id)
        leg = get_object_or_404(
            TranshipmentLeg, pk=leg_id, booking=booking
        )

        # Update fields on the leg
        if 'port' in data:
            leg.port = data['port']
        if 'eta' in data:
            leg.eta = data['eta']
        if 'etd' in data:
            leg.etd = data['etd']
        if 'connecting_vessel_voyage' in data:
            leg.connecting_vessel_voyage = data['connecting_vessel_voyage']

        # Validate ETD > ETA for this leg
        if leg.etd <= leg.eta:
            raise serializers.ValidationError({
                'etd': ['ETD must be strictly later than ETA at the same port.']
            })

        # Build the full list of legs for chronological validation
        all_legs = list(
            booking.transhipment_legs.exclude(pk=leg.pk)
            .order_by('sequence')
            .values('eta', 'etd', 'sequence')
        )
        # Insert the updated leg at its proper position
        updated_leg_data = {'eta': leg.eta, 'etd': leg.etd, 'sequence': leg.sequence}
        all_legs.append(updated_leg_data)
        all_legs.sort(key=lambda x: x['sequence'])

        # Validate chronological ordering
        validate_transhipment_legs_chronology(all_legs)

        leg.save()
        return leg

    @staticmethod
    def remove_transhipment(booking_id, leg_id, user):
        """
        Remove a transhipment leg and re-sequence remaining legs.

        Args:
            booking_id: ID of the booking.
            leg_id: ID of the transhipment leg to remove.
            user: The authenticated user performing the action.

        Raises:
            Http404 if booking or leg not found.
        """
        booking = get_object_or_404(Booking, pk=booking_id)
        leg = get_object_or_404(
            TranshipmentLeg, pk=leg_id, booking=booking
        )

        leg.delete()

        # Re-sequence remaining legs
        remaining_legs = booking.transhipment_legs.order_by('sequence')
        for i, remaining_leg in enumerate(remaining_legs, start=1):
            if remaining_leg.sequence != i:
                remaining_leg.sequence = i
                remaining_leg.save(update_fields=['sequence'])

    # Valid status transitions: current_status -> [allowed next statuses]
    VALID_TRANSITIONS = {
        Booking.Status.PENDING: [Booking.Status.DO_BOOKING_EDIT],
        Booking.Status.DO_BOOKING_EDIT: [Booking.Status.COMPLETED],
        Booking.Status.COMPLETED: [],
    }

    # Mandatory fields that must be populated before transitioning to COMPLETED
    MANDATORY_FIELDS_FOR_COMPLETION = [
        'booking_date',
        'booking_validity_date',
        'shipping_line',
        'pol',
        'pod',
        'client',
        'cargo_type',
        'commodity',
        'shipment_type',
        'stuffing_type',
        'forwarding_window_start',
        'forwarding_window_end',
    ]

    @classmethod
    def change_status(cls, booking_id, new_status, user):
        """
        Change the status of a booking with state machine enforcement.

        Args:
            booking_id: ID of the booking to update.
            new_status: The target status value.
            user: The authenticated user performing the change.

        Returns:
            The updated Booking instance.

        Raises:
            Http404 if booking not found.
            serializers.ValidationError if transition is invalid or
                mandatory fields are missing for COMPLETED transition.
        """
        booking = get_object_or_404(Booking, pk=booking_id)

        previous_status = booking.status

        # Validate transition
        allowed = cls.VALID_TRANSITIONS.get(previous_status, [])
        if new_status not in allowed:
            if allowed:
                allowed_display = ', '.join(
                    Booking.Status(s).label for s in allowed
                )
                raise serializers.ValidationError({
                    'status': (
                        f'Invalid status transition from '
                        f'"{Booking.Status(previous_status).label}" to '
                        f'"{Booking.Status(new_status).label}". '
                        f'Allowed next status: {allowed_display}.'
                    )
                })
            else:
                raise serializers.ValidationError({
                    'status': (
                        f'Invalid status transition. '
                        f'"{Booking.Status(previous_status).label}" is a terminal '
                        f'status and cannot be changed.'
                    )
                })

        # If transitioning to COMPLETED, validate all mandatory fields
        if new_status == Booking.Status.COMPLETED:
            missing_fields = []
            for field_name in cls.MANDATORY_FIELDS_FOR_COMPLETION:
                value = getattr(booking, field_name, None)
                if value is None or value == '':
                    missing_fields.append(field_name)

            if missing_fields:
                raise serializers.ValidationError({
                    'status': (
                        f'Cannot transition to Completed. The following mandatory '
                        f'fields are missing: {", ".join(missing_fields)}.'
                    )
                })

        # Perform the transition
        booking.status = new_status
        booking.save(update_fields=['status'])

        # Create status history record
        BookingStatusHistory.objects.create(
            booking=booking,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=user,
        )

        # Queue onboard confirmation email when transitioning to COMPLETED
        if new_status == Booking.Status.COMPLETED:
            try:
                from notifications.tasks import send_onboard_confirmation_task
                send_onboard_confirmation_task.delay(booking.id)
            except Exception:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(
                    'Failed to queue onboard confirmation email for booking %s',
                    booking.id,
                )

        return booking
