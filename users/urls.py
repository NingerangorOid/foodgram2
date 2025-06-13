from django.urls import path
from djoser.views import TokenCreateView, TokenDestroyView
from users.views import UserViewSet, RegisterView, UserTokenView, SubscriptionViewSet

urlpatterns = [
    # Users endpoints
    path('api/users/',
         UserViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='users-list'),
    path('api/users/me/',
         UserViewSet.as_view({'get': 'me', 'put': 'me', 'patch': 'me'}),
         name='users-me'),
    path('api/users/set_password/',
         UserViewSet.as_view({'post': 'set_password'}),
         name='users-set-password'),
    path('api/users/me/avatar/',
         UserViewSet.as_view({'put': 'manage_avatar', 'patch': 'manage_avatar', 'delete': 'manage_avatar'}),
         name='users-manage-avatar'),
    path('api/users/<pk>/',
         UserViewSet.as_view({'get': 'retrieve', 'put': 'update',
                              'patch': 'partial_update', 'delete': 'destroy'}),
         name='users-detail'),
    # Получить список подписок
    path('api/users/subscriptions/', SubscriptionViewSet.as_view({'get': 'list'}),
         name='subscriptions'),

    # Подписка/отписка
    path('api/users/<int:pk>/subscribe/',
         SubscriptionViewSet.as_view({'post': 'subscribe', 'delete': 'subscribe'}),
         name='subscribe'),

    # Authentication endpoints
    path('api/auth/register/',
         RegisterView.as_view(),
         name='register'),
    path('api/auth/token/',
         UserTokenView.as_view(),
         name='token'),
    path('api/auth/token/login/',
         TokenCreateView.as_view(),
         name='login'),
    path('api/auth/token/logout/',
         TokenDestroyView.as_view(),
         name='logout'),
]