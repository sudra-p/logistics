"""
Create PostgreSQL sequence for booking job number generation.
This migration is a no-op on SQLite (test environments).
"""

from django.db import migrations


def create_sequence(apps, schema_editor):
    """Create the PostgreSQL sequence for job numbers. Skip on non-PostgreSQL backends."""
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(
            "CREATE SEQUENCE IF NOT EXISTS booking_job_number_seq START 1;"
        )


def drop_sequence(apps, schema_editor):
    """Drop the PostgreSQL sequence. Skip on non-PostgreSQL backends."""
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute("DROP SEQUENCE IF EXISTS booking_job_number_seq;")


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_sequence, drop_sequence),
    ]
