"""
Tests for Proforma Invoice status transitions.
Task 25.2: Test valid and invalid PI status transitions.
"""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

from master_data.models import Client
from proforma.models import ProformaInvoice, ProformaLineItem
from proforma.services import ProformaService

User = get_user_model()


@pytest.fixture
def accounts_user(db):
    user = User.objects.create_user(username='accounts_user', password='testpass123')
    group, _ = Group.objects.get_or_create(name='Accounts')
    user.groups.add(group)
    return user


@pytest.fixture
def client_obj(db):
    return Client.objects.create(name='Test Client', email='client@test.com')


@pytest.fixture
def draft_pi(accounts_user, client_obj):
    """Create a DRAFT ProformaInvoice."""
    pi = ProformaInvoice(
        date=datetime.date.today(),
        customer=client_obj,
        currency='USD',
        payment_terms='Net 30',
        expected_shipment_date=datetime.date.today(),
        status=ProformaInvoice.Status.DRAFT,
        created_by=accounts_user,
    )
    pi.save()
    ProformaLineItem.objects.create(
        proforma_invoice=pi,
        product_name='Widget',
        quantity=Decimal('10.000'),
        rate=Decimal('100.00'),
        amount=Decimal('1000.00'),
    )
    pi.total_amount = Decimal('1000.00')
    pi.save(update_fields=['total_amount'])
    return pi


@pytest.mark.django_db
class TestValidStatusTransitions:
    """Tests for allowed PI status transitions."""

    def test_draft_to_sent(self, draft_pi, accounts_user):
        """DRAFT -> SENT is valid."""
        pi = ProformaService.change_status(draft_pi.pk, 'SENT', accounts_user)
        assert pi.status == ProformaInvoice.Status.SENT

    def test_sent_to_approved(self, draft_pi, accounts_user):
        """SENT -> APPROVED is valid."""
        ProformaService.change_status(draft_pi.pk, 'SENT', accounts_user)
        pi = ProformaService.change_status(draft_pi.pk, 'APPROVED', accounts_user)
        assert pi.status == ProformaInvoice.Status.APPROVED

    def test_approved_to_payment_pending(self, draft_pi, accounts_user):
        """APPROVED -> PAYMENT_PENDING is valid."""
        ProformaService.change_status(draft_pi.pk, 'SENT', accounts_user)
        ProformaService.change_status(draft_pi.pk, 'APPROVED', accounts_user)
        pi = ProformaService.change_status(draft_pi.pk, 'PAYMENT_PENDING', accounts_user)
        assert pi.status == ProformaInvoice.Status.PAYMENT_PENDING

    def test_payment_pending_to_paid(self, draft_pi, accounts_user):
        """PAYMENT_PENDING -> PAID is valid."""
        ProformaService.change_status(draft_pi.pk, 'SENT', accounts_user)
        ProformaService.change_status(draft_pi.pk, 'APPROVED', accounts_user)
        ProformaService.change_status(draft_pi.pk, 'PAYMENT_PENDING', accounts_user)
        pi = ProformaService.change_status(draft_pi.pk, 'PAID', accounts_user)
        assert pi.status == ProformaInvoice.Status.PAID

    def test_full_lifecycle(self, draft_pi, accounts_user):
        """Can traverse the entire status lifecycle."""
        statuses = ['SENT', 'APPROVED', 'PAYMENT_PENDING', 'PAID']
        for status_val in statuses:
            pi = ProformaService.change_status(draft_pi.pk, status_val, accounts_user)
        assert pi.status == ProformaInvoice.Status.PAID


@pytest.mark.django_db
class TestInvalidStatusTransitions:
    """Tests for rejected PI status transitions."""

    def test_draft_to_approved_rejected(self, draft_pi, accounts_user):
        """DRAFT -> APPROVED is not allowed (must go through SENT)."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            ProformaService.change_status(draft_pi.pk, 'APPROVED', accounts_user)
        assert 'status' in exc_info.value.detail

    def test_draft_to_paid_rejected(self, draft_pi, accounts_user):
        """DRAFT -> PAID is not allowed."""
        with pytest.raises(serializers.ValidationError):
            ProformaService.change_status(draft_pi.pk, 'PAID', accounts_user)

    def test_sent_to_draft_rejected(self, draft_pi, accounts_user):
        """SENT -> DRAFT (backward) is not allowed."""
        ProformaService.change_status(draft_pi.pk, 'SENT', accounts_user)
        with pytest.raises(serializers.ValidationError):
            ProformaService.change_status(draft_pi.pk, 'DRAFT', accounts_user)

    def test_paid_to_any_rejected(self, draft_pi, accounts_user):
        """PAID is a terminal status, no transitions allowed."""
        ProformaService.change_status(draft_pi.pk, 'SENT', accounts_user)
        ProformaService.change_status(draft_pi.pk, 'APPROVED', accounts_user)
        ProformaService.change_status(draft_pi.pk, 'PAYMENT_PENDING', accounts_user)
        ProformaService.change_status(draft_pi.pk, 'PAID', accounts_user)

        with pytest.raises(serializers.ValidationError) as exc_info:
            ProformaService.change_status(draft_pi.pk, 'DRAFT', accounts_user)
        assert 'terminal' in str(exc_info.value.detail['status']).lower() or 'Cannot' in str(exc_info.value.detail['status'])

    def test_skip_status_rejected(self, draft_pi, accounts_user):
        """Cannot skip intermediate statuses."""
        with pytest.raises(serializers.ValidationError):
            ProformaService.change_status(draft_pi.pk, 'PAYMENT_PENDING', accounts_user)
