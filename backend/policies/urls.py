from django.urls import path, include
from .views import PolicyViewSet, CenterViewSet, MapPOIViewSet

urlpatterns = [
    # POI / Centers (순서가 중요함)
    path('centers/', CenterViewSet.as_view({'get': 'list'}), name='center-list'),
    path('map/pois/', MapPOIViewSet.as_view({'get': 'list'}), name='map-poi'),

    # Policy Action ViewSets (순서가 중요함)
    path('deadline_soon/', PolicyViewSet.as_view({'get': 'deadline_soon'}), name='policy-deadline-soon'),
    path('recommended/', PolicyViewSet.as_view({'get': 'recommended'}), name='policy-recommended'),
    path('calendar/', PolicyViewSet.as_view({'get': 'calendar'}), name='policy-calendar'),

    # Standard Policy ViewSets
    path('', PolicyViewSet.as_view({'get': 'list'}), name='policy-list'),
    path('<str:pk>/', PolicyViewSet.as_view({'get': 'retrieve'}), name='policy-detail'),
]