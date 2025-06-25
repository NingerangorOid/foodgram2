from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from core.pagination import CustomPagination
from api.models import Ingredient, Recipe, Favorite, ShoppingCart, RecipeIngredient
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    IngredientSerializer, RecipeSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer, RecipeShortLinkSerializer, ShoppingCartRecipeSerializer, FavoriteRecipeSerializer
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


class RecipeShortLinkViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeShortLinkSerializer
    permission_classes = [AllowAny]  # Можешь изменить на нужные разрешения
    lookup_field = 'pk'  # По умолчанию используется 'pk', но можно задать и 'id'

    http_method_names = ['get']  # Разрешаем только GET-запросы

    def retrieve(self, request, *args, **kwargs):
        recipe = self.get_object()
        serializer = self.get_serializer(recipe)
        return Response(serializer.data)


class ShoppingCartViewSet(viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()
    serializer_class = ShoppingCartRecipeSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        user = self.request.user
        recipe_ids = ShoppingCart.objects.filter(user=user).values_list('recipe_id', flat=True)
        return Recipe.objects.filter(id__in=recipe_ids)

    def get_serializer_context(self):
        """Передаем request в контекст сериалайзера"""
        return {'request': self.request}

    def create(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        user = request.user

        # 1. Получаем рецепт или 404
        recipe = get_object_or_404(Recipe, id=recipe_id)

        # 2. Нельзя добавить свой рецепт
        if recipe.author == user:
            return Response(
                {'error': 'Нельзя добавить свой рецепт в корзину'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Уже в корзине?
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {'error': 'Рецепт уже в корзине'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Создаём запись в корзине
        cart_item = ShoppingCart.objects.create(user=user, recipe=recipe)

        # 5. Сериализуем напрямую через наш простой сериалайзер
        serializer = ShoppingCartRecipeSerializer(instance=cart_item, context={'request': request})

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        context = self.get_serializer_context()
        return self.serializer_class(instance, data=data, many=many, partial=partial, context=context)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted, _ = ShoppingCart.objects.filter(recipe=instance.recipe, user=request.user).delete()
        if not deleted:
            return Response({'error': 'Рецепт не был в корзине'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_object(self):
        recipe_id = self.kwargs.get('pk')
        if not recipe_id:
            raise NotFound("Не указан ID рецепта")

        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            raise NotFound("Рецепт не существует")

        cart_item = ShoppingCart.objects.filter(recipe=recipe, user=self.request.user).first()
        if not cart_item:
            raise ValidationError("Рецепт не был добавлен в корзину", code="not_in_cart")

        return cart_item

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user

        ingredients = RecipeIngredient.objects.filter(
            recipe__in_shopping_cart__user=user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount'))

        if not ingredients.exists():
            return Response({'error': 'Корзина пуста'}, status=status.HTTP_400_BAD_REQUEST)

        content = []
        for item in ingredients:
            content.append(
                f"{item['ingredient__name']} — {item['total_amount']} {item['ingredient__measurement_unit']}\n"
            )

        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response


class FavoriteViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = FavoriteRecipeSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']
    pagination_class = CustomPagination  # если используешь пагинацию

    def get_queryset(self):
        user = self.request.user
        recipe_ids = Favorite.objects.filter(user=user).values_list('recipe_id', flat=True)
        return Recipe.objects.filter(id__in=recipe_ids)

    def list(self, request, *args, **kwargs):
        """GET /api/recipes/favorite/"""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """POST /api/recipes/<int:pk>/favorite/"""
        recipe_id = kwargs.get('pk')
        user = request.user
        recipe = get_object_or_404(Recipe, id=recipe_id)

        if recipe.author == user:
            return Response(
                {'error': 'Нельзя добавить свой рецепт в избранное'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Favorite.objects.filter(recipe=recipe, user=user).exists():
            return Response(
                {'error': 'Рецепт уже в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )

        Favorite.objects.create(recipe=recipe, user=user)
        serializer = self.get_serializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """DELETE /api/recipes/<int:pk>/favorite/"""
        recipe = self.get_object()
        user = request.user

        deleted, _ = Favorite.objects.filter(recipe=recipe, user=user).delete()
        if not deleted:
            return Response({'error': 'Рецепт не был в избранном'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_object(self):
        recipe_id = self.kwargs.get('pk')
        recipe = get_object_or_404(Recipe, id=recipe_id)
        return recipe

    def get_serializer_context(self):
        return {'request': self.request}