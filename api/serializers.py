import base64
import uuid
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from users.serializers import CustomUserSerializer
from api.models import (
    Ingredient, Recipe, RecipeIngredient, Favorite, ShoppingCart
)


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            id = uuid.uuid4()
            data = ContentFile(base64.b64decode(imgstr), name=f'{id}.{ext}')
        return super().to_internal_value(data)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        if Favorite.objects.filter(
                user=data['user'], recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError(
                'Рецепт уже в избранном'
            )
        return data

    def to_representation(self, instance):
        return {
            'id': instance.recipe.id,
            'name': instance.recipe.name,
            'image': instance.recipe.image.url,
            'cooking_time': instance.recipe.cooking_time
        }


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, data):
        if ShoppingCart.objects.filter(
                user=data['user'], recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError(
                'Рецепт уже в корзине'
            )
        return data

    def to_representation(self, instance):
        return {
            'id': instance.recipe.id,
            'name': instance.recipe.name,
            'image': instance.recipe.image.url,
            'cooking_time': instance.recipe.cooking_time
        }


class RecipeSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    ingredients_in_db = RecipeIngredientSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image_in_db = serializers.SerializerMethodField()

    # Для записи
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True
    )
    image = Base64ImageField(write_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
            'ingredients_in_db', 'image_in_db',
        )

    def get_image_in_db(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from api.models import Favorite
            return Favorite.objects.filter(user=request.user, recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from api.models import ShoppingCart
            return ShoppingCart.objects.filter(user=request.user, recipe=obj).exists()
        return False

    def validate_ingredients(self, value):
        if not value or len(value) == 0:
            raise ValidationError('Добавьте хотя бы один ингредиент')

        seen_ids = set()
        for item in value:
            if 'id' not in item:
                raise ValidationError('У ингредиента должно быть поле "id"')
            if 'amount' not in item:
                raise ValidationError('У ингредиента должно быть поле "amount"')

            try:
                ingredient_id = int(item['id'])
                amount = int(item['amount'])
            except (TypeError, ValueError):
                raise ValidationError('ID и количество должны быть целыми числами')

            if ingredient_id in seen_ids:
                raise ValidationError(f'Ингредиент с ID {ingredient_id} повторяется')
            seen_ids.add(ingredient_id)

            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise ValidationError(f'Ингредиент с ID {ingredient_id} не существует')

            if amount <= 0:
                raise ValidationError('Количество должно быть больше нуля')

        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        image_data = validated_data.pop('image')
        validated_data.pop('author', None)
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            image=image_data,
            **validated_data
        )

        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=item['id'],
                amount=item['amount']
            ) for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        recipe.save()
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.get('ingredients')  # Не используем pop(), чтобы не терять информацию

        if ingredients_data is None:
            raise ValidationError({'ingredients': ['Это поле обязательно']})

        image_data = validated_data.pop('image', None)

        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get('cooking_time', instance.cooking_time)

        if image_data:
            instance.image = image_data

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            recipe_ingredients = [
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=item['id'],
                    amount=item['amount']
                ) for item in ingredients_data
            ]
            RecipeIngredient.objects.bulk_create(recipe_ingredients)

        instance.save()
        return instance

    def to_representation(self, instance):
        # Сначала проверяем флаг

        data = super().to_representation(instance)

        if 'ingredients_in_db' in data:
            data['ingredients'] = data['ingredients_in_db']
            data.pop('ingredients_in_db', None)

        if 'image_in_db' in data:
            data['image'] = data['image_in_db']
            data.pop('image_in_db', None)

        return data


class RecipeShortLinkSerializer(serializers.Serializer):
    short_link = serializers.URLField(read_only=True)

    def to_representation(self, instance):
        return {'short_link': instance.short_link}