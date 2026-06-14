from django.urls import path

from .views import MasterDataViewSet

app_name = 'master_data'

# Wire up list/create and retrieve/update/destroy for each entity type.
# URL pattern: /api/master-data/{entity_type}/ and /api/master-data/{entity_type}/{pk}/
master_data_list = MasterDataViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
master_data_detail = MasterDataViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

urlpatterns = [
    path('<str:entity_type>/', master_data_list, name='entity-list'),
    path('<str:entity_type>/<int:pk>/', master_data_detail, name='entity-detail'),
]
