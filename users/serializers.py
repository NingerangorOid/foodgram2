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

