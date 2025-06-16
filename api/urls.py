from django.urls import path
from api.views import IngredientViewSet, RecipeViewSet, RecipeShortLinkViewSet, ShoppingCartViewSet, FavoriteViewSet

urlpatterns = [
    # Ingredients endpoints
    path('api/ingredients/',
         IngredientViewSet.as_view({'get': 'list'}),
         name='ingredients-list'),
    path('api/ingredients/<pk>/',
         IngredientViewSet.as_view({'get': 'retrieve'}),
         name='ingredients-detail'),
    # Recipes endpoints
    path('api/recipes/',
         RecipeViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='recipes-list'),
    path('api/recipes/download_shopping_cart/',
         ShoppingCartViewSet.as_view({'get': 'download_shopping_cart'}),
         name='get-shopping-cart'),
    path('api/recipes/<int:pk>/shopping_cart/',
         ShoppingCartViewSet.as_view({'get': 'list', 'post': 'create', 'delete': 'destroy'}),
         name='shopping-cart-detail'),

    path('api/recipes/<int:pk>/favorite/',
         FavoriteViewSet.as_view({'get': 'list', 'post': 'create', 'delete': 'destroy'}),
         name='recipe-favorite'),

    path('api/recipes/<pk>/',
         RecipeViewSet.as_view({'get': 'retrieve', 'put': 'update',
                                'patch': 'partial_update', 'delete': 'destroy'}),
         name='recipes-detail'),
    path('api/recipes/<pk>/get-link/',
         RecipeShortLinkViewSet.as_view({'get': 'retrieve'}), name='recipe-link'),
]