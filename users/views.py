from rest_framework import generics, status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from rest_framework.views import APIView

from core.pagination import CustomPagination
from users.models import Subscription
from users.serializers import (
    CustomUserSerializer, SetPasswordSerializer, AvatarSerializer, TokenSerializer, SubscriptionSerializer
)
from rest_framework.decorators import action


User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer

    http_method_names = ['get', 'post', 'put', 'delete']

    def get_permissions(self):
        if self.action in ['me', 'set_password', 'manage_avatar']:
            return [IsAuthenticated()]
        return [AllowAny()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Хешируем пароль
        user.set_password(request.data['password'])
        user.save()

        # Создаём токен
        token, created = Token.objects.get_or_create(user=user)

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name
            },
            status=status.HTTP_201_CREATED
        )

    @action(
        methods=['get'],
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def get_own_avatar(self, request):
        user = request.user
        if not user.avatar:
            raise NotFound("Аватар не установлен")
        serializer = AvatarSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=['get'],
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        methods=['post'],
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_password = serializer.validated_data['current_password']
        new_password = serializer.validated_data['new_password']

        if not request.user.check_password(current_password):
            return Response(
                {'current_password': 'Неверный текущий пароль'},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(new_password)
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['put', 'delete'],
        detail=False,
        permission_classes=[IsAuthenticated],
        url_path='avatar'
    )
    def manage_avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarSerializer(instance=user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        # DELETE: удаление аватара
        if user.avatar:
            user.avatar.delete()
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, pk=None):
        author = self.get_object()
        user = request.user

        if request.method == 'POST':
            if user == author:
                return Response(
                    {"error": "Нельзя подписаться на себя"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Subscription.objects.filter(user=user, author=author).exists():
                return Response(
                    {"error": "Вы уже подписаны"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(user=user, author=author)
            return Response({"success": True}, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            subscription = Subscription.objects.filter(user=user, author=author).first()
            if not subscription:
                return Response(
                    {"error": "Вы не подписаны"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Получаем токен для нового пользователя
        token, created = Token.objects.get_or_create(user=user)

        # Возвращаем данные пользователя и токен
        return Response({
            'user': CustomUserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)


class UserTokenView(generics.RetrieveAPIView):
    queryset = Token.objects.all()
    serializer_class = TokenSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        token, created = Token.objects.get_or_create(user=self.request.user)
        return token


class SubscriptionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def list(self, request):
        print('', '', sep=r'/n'*100)
        queryset = Subscription.objects.filter(user=request.user)

        if not queryset.exists():
            return Response(
                {'detail': 'У вас пока нет подписок'},
                status=status.HTTP_200_OK
            )

        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = SubscriptionSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def subscribe(self, request, pk=None):
        user = request.user

        try:
            author = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

        if user.id == pk:
            return Response({'error': 'Нельзя подписаться на себя'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'POST':
            subscription, created = Subscription.objects.get_or_create(user=user, author=author)
            if not created:
                return Response({'error': 'Вы уже подписаны'}, status=status.HTTP_400_BAD_REQUEST)

            serializer = SubscriptionSerializer(subscription, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            deleted, _ = Subscription.objects.filter(user=user, author_id=pk).delete()
            if not deleted:
                return Response({'error': 'Вы не подписаны'}, status=status.HTTP_400_BAD_REQUEST)

            return Response(status=status.HTTP_204_NO_CONTENT)