from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
from users.models import Subscription
import base64
import uuid
from django.core.files.base import ContentFile


User = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)

    password = serializers.CharField(
        write_only=True,
        required=False,  # Не обязательное по умолчанию
        min_length=6,
        error_messages={
            'min_length': 'Пароль должен содержать не менее 6 символов.',
            'required': 'Поле "password" обязательно для заполнения.'
        }
    )

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name',
            'email', 'password', 'is_subscribed', 'avatar'
        )
        read_only_fields = ('is_subscribed',)

    def validate(self, data):
        request = self.context.get('request')
        # При регистрации пароль обязателен
        if request and request.method == 'POST' and 'password' not in data:
            raise serializers.ValidationError({
                'password': ['Обязательное поле.']
            })
        return data

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, author=obj
            ).exists()
        return False

    def get_auth_token(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj == request.user:
            token, created = Token.objects.get_or_create(user=obj)
            return token.key
        return None

    def create(self, validated_data):
        """Создание пользователя с хешированием пароля"""
        password = validated_data.pop('password')
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        """Обновление пользователя, с возможностью изменения пароля"""
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class SetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            id = uuid.uuid4()
            data = ContentFile(base64.b64decode(imgstr), name=f'{id}.{ext}')
        return super().to_internal_value(data)


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = ('key', 'user')


class SubscriptionSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='author.id')
    username = serializers.CharField(source='author.username')
    first_name = serializers.CharField(source='author.first_name')
    last_name = serializers.CharField(source='author.last_name')
    email = serializers.EmailField(source='author.email')
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    class Meta:
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'is_subscribed', 'avatar', 'recipes_count', 'recipes'
        ]

    def get_is_subscribed(self, obj):
        return True  # Потому что мы уже подписаны

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.author.avatar:
            return request.build_absolute_uri(obj.author.avatar.url)
        return None

    def get_author(self, obj):
        user = obj.author
        return {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'is_subscribed': Subscription.objects.filter(
                user=obj.user, author=user
            ).exists(),
            'avatar': self.context['request'].build_absolute_uri(user.avatar.url) if user.avatar else None,
        }

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')

        recipes = obj.author.recipes.all()

        if recipes_limit:
            try:
                recipes = recipes[:int(recipes_limit)]
            except ValueError:
                raise serializers.ValidationError("recipes_limit должен быть числом")

        return [
            {
                'id': r.id,
                'name': r.name,
                'image': request.build_absolute_uri(r.image.url) if r.image else None,
                'cooking_time': r.cooking_time
            }
            for r in recipes
        ]

    def to_representation(self, instance):
        # Получаем данные автора
        author_data = self.get_author(instance)

        # Возвращаем структуру, где поля автора находятся на верхнем уровне
        return {
            'id': author_data['id'],
            'username': author_data['username'],
            'first_name': author_data['first_name'],
            'last_name': author_data['last_name'],
            'email': author_data['email'],
            'is_subscribed': author_data['is_subscribed'],
            'avatar': author_data['avatar'],
            'recipes_count': self.get_recipes_count(instance),
            'recipes': self.get_recipes(instance)
        }

    def validate(self, data):
        request = self.context.get('request')
        view = self.context.get('view')
        user = request.user
        author_id = view.kwargs.get('pk')

        if not User.objects.filter(id=author_id).exists():
            raise serializers.ValidationError("Пользователь не существует")

        if user.id == author_id:
            raise serializers.ValidationError("Нельзя подписаться на себя")

        return {
            'user': user,
            'author_id': author_id
        }

    def create(self, validated_data):
        return Subscription.objects.create(**validated_data)

    def delete(self):
        user = self.context.get('request').user
        author_id = self.context.get('view').kwargs.get('pk')
        Subscription.objects.filter(user=user, author_id=author_id).delete()