from django.urls import path
from api.views import IngredientViewSet, RecipeViewSet

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
         RecipeViewSet.as_view({'get': 'download_shopping_cart'}),
         name='recipes-download-shopping-cart'),
    path('api/recipes/<pk>/',
         RecipeViewSet.as_view({'get': 'retrieve', 'put': 'update',
                              'patch': 'partial_update', 'delete': 'destroy'}),
         name='recipes-detail'),
    path('api/recipes/<pk>/favorite/',
         RecipeViewSet.as_view({'post': 'favorite', 'delete': 'unfavorite'}),
         name='recipes-favorite'),
    path('api/recipes/<pk>/shopping_cart/',
         RecipeViewSet.as_view({'post': 'add_to_shopping_cart',
                              'delete': 'remove_from_shopping_cart'}),
         name='recipes-shopping-cart'),
]