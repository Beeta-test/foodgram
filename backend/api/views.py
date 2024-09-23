import csv
import io

from django.db.models import Sum
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Tag)
from rest_framework import decorators, permissions, response, status, viewsets
from users.models import CustomUser, Subscribe

from .filters import IngredientFilter, RecipeFilter
from .pagination import LimitPageNumberPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (AuthorSerializer, CreateRecipeSerializer,
                          FavoriteSerializer, IngredientSerializer,
                          RecipeSerializer, ShoppingCartSerializer,
                          ShortRecipeSerializer, SubscribeSerializer,
                          TagSerializer, UserAvatarSerializer, UserSerializer)
from backend.consts import BASE_URl


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = LimitPageNumberPagination
    ordering = ['-pub_date']
    permission_classes = (IsAuthorOrReadOnly,
                          permissions.IsAuthenticatedOrReadOnly)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateRecipeSerializer
        return RecipeSerializer

    def remove_item(self, model, request, pk=None):
        recipe = self.get_object()
        user = request.user

        delete_count, _ = model.objects.filter(
            user=user, recipe=recipe).delete()

        if delete_count > 0:
            return response.Response(status=status.HTTP_204_NO_CONTENT)
        return response.Response(status=status.HTTP_400_BAD_REQUEST)

    @decorators.action(
        detail=True,
        methods=['post'],
        permission_classes=(permissions.IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        serializer = FavoriteSerializer(
            data={'user': user.id, 'recipe': recipe.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ShortRecipeSerializer(
            recipe, context={'request': request})
        return response.Response(
            response_serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def remove_favorite(self, request, pk=None):
        return self.remove_item(Favorite, request, pk)

    @decorators.action(
        detail=True,
        methods=['post'],
        permission_classes=(permissions.IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        serializer = ShoppingCartSerializer(
            data={'user': user.id, 'recipe': recipe.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ShortRecipeSerializer(
            recipe, context={'request': request})
        return response.Response(
            response_serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk=None):
        return self.remove_item(ShoppingList, request, pk)

    @decorators.action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        shopping_lists = ShoppingList.objects.filter(user=request.user)
        recipes = shopping_lists.values_list('recipe', flat=True)

        ingredients = RecipeIngredient.objects.filter(recipe__in=recipes) \
            .values('ingredient__name', 'ingredient__measurement_unit') \
            .annotate(total_amount=Sum('amount'))

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['Ingredient', 'Amount', 'Unit'])

        for ingredient in ingredients:
            writer.writerow([
                ingredient['ingredient__name'],
                ingredient['total_amount'],
                ingredient['ingredient__measurement_unit']
            ])

        buffer.seek(0)
        response = io.BytesIO(buffer.getvalue().encode('utf-8'))
        buffer.close()

        return FileResponse(
            response,
            as_attachment=True,
            filename='shopping_cart.csv'
        )

    @decorators.action(
        detail=True,
        methods=['get'],
        url_path='get-link',
    )
    def get_link(self, request, *args, **kwargs):
        recipe = self.get_object()
        short_link = recipe.short_link
        return response.Response({'short-link': BASE_URl + short_link})

    def redirect_recipe(request, link):
        id = Recipe.objects.get(short_link=link).id
        foodgram_link = str.replace(
            request.build_absolute_uri(), 's/' + link + '/', '')
        return HttpResponseRedirect(
            foodgram_link + 'recipes/' + str(id) + '/')


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAuthorOrReadOnly,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter
    permission_classes = (IsAuthorOrReadOnly,)
    pagination_class = None


class CustomUserViewSet(UserViewSet):
    serializer_class = AuthorSerializer
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = LimitPageNumberPagination

    @decorators.action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated])
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @decorators.action(
        detail=False,
        methods=['get'],
    )
    def subscriptions(self, request):
        user_subscriptions = CustomUser.objects.filter(
            followers__user=request.user
        )
        page = self.paginate_queryset(user_subscriptions)
        recipes_limit = request.query_params.get('recipes_limit', None)

        serializer = UserSerializer(
            page,
            many=True,
            context={
                'request': request,
                'recipes_limit': recipes_limit
            }
        )

        return self.get_paginated_response(serializer.data)

    @decorators.action(
        detail=True,
        methods=['post'],
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(CustomUser, id=id)
        data = {'user': request.user.id, 'author': author.id}

        serializer = SubscribeSerializer(
            data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        user_serializer = UserSerializer(
            author,
            context={
                'request': request,
                'recipes_limit': request.query_params.get('recipes_limit')
            }
        )

        return response.Response(
            user_serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id):
        author = get_object_or_404(CustomUser, id=id)

        subscription = Subscribe.objects.filter(
            user=request.user, author=author)
        if subscription.exists():
            subscription.delete()
            return response.Response(status=status.HTTP_204_NO_CONTENT)

        return response.Response(status=status.HTTP_400_BAD_REQUEST)

    @decorators.action(
        detail=False,
        methods=['put'],
        url_path='me/avatar',
    )
    def update_avatar(self, request):
        user = request.user

        serializer = UserAvatarSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return response.Response(
            serializer.data, status=status.HTTP_200_OK
        )

    @update_avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user

        user.avatar.delete()
        user.save()

        return response.Response(status=status.HTTP_204_NO_CONTENT)
