from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from core.pagination import CustomPagination
from api.models import Ingredient, Recipe, Favorite, ShoppingCart, RecipeIngredient
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    IngredientSerializer, RecipeSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer, RecipeShortLinkSerializer
)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = CustomPagination
    permission_classes = [IsAuthorOrReadOnly]

    serializer_class = RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthorOrReadOnly()]
        return super().get_permissions()

    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user

        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'error': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=user, recipe=recipe)
            return Response(
                {
                    'id': recipe.id,
                    'name': recipe.name,
                    'cooking_time': recipe.cooking_time,
                    'image': recipe.image.url
                },
                status=status.HTTP_201_CREATED
            )

        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            Favorite.objects.filter(user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Рецепт не в избранном'}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'error': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            return Response(
                {
                    'id': recipe.id,
                    'name': recipe.name,
                    'cooking_time': recipe.cooking_time,
                    'image': recipe.image.url
                },
                status=status.HTTP_201_CREATED
            )

        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            ShoppingCart.objects.filter(user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Рецепт не в списке покупок'}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=['get'],
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__in_shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount'))

        shopping_list = ['Список покупок:\n']
        for item in ingredients:
            shopping_list.append(
                f"{item['ingredient__name']} - {item['total_amount']} {item['ingredient__measurement_unit']}\n"
            )

        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response


class RecipeShortLinkViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeShortLinkSerializer
    permission_classes = [AllowAny]  # Можешь изменить на нужные разрешения
    lookup_field = 'pk'  # По умолчанию используется 'pk', но можно задать и 'id'

    http_method_names = ['get']  # Разрешаем только GET-запросы

    def retrieve(self, request, *args, **kwargs):
        recipe = self.get_object()
        serializer = self.get_serializer(recipe)
        print(serializer.data, '1', sep=r'/n'*100)
        return Response(serializer.data)