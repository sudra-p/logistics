"""
Test settings - uses SQLite for running tests without PostgreSQL.
"""

from logistics.settings import *  # noqa: F401, F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Celery test configuration - run tasks synchronously without a broker
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False
