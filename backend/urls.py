from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, IngredientViewSet,
    TagViewSet, RecipeViewSet,
    TokenCreateView, TokenDestroyView
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('tags', TagViewSet, basename='tags')
router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/login/', TokenCreateView.as_view(), name='login'),
    path('auth/token/logout/', TokenDestroyView.as_view(), name='logout'),
]