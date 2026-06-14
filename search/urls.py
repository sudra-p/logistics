from django.urls import path

from search.views import BookingSearchView

app_name = 'search'

urlpatterns = [
    path('', BookingSearchView.as_view(), name='booking-search'),
]
