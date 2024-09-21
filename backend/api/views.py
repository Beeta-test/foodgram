import csv
import hashlib
import io

from core.consts import BASE_URl
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Tag)
from rest_framework import (decorators, exceptions, filters, permissions,
                            response, status, viewsets)
from users.models import CustomUser, Subscribe

from .filters import IngredientFilter, RecipeFilter
from .pagination import LimitPageNumberPagination
from .serializers import (AuthorSerializer, CreateRecipeSerializer,
                          CustomUserSerializer, IngredientSerializer,
                          RecipeSerializer, ShortRecipeSerializer,
                          TagSerializer)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = RecipeFilter
    pagination_class = LimitPageNumberPagination
    ordering = ['-pub_date']

    def get_queryset(self):
        queryset = Recipe.objects.all()
        user = self.request.user

        is_favorited = self.request.query_params.get(
            'is_favorited', None)
        if is_favorited == '1' and user.is_authenticated:
            queryset = queryset.filter(favorited_by__user=user)

        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart', None)
        if is_in_shopping_cart == '1' and user.is_authenticated:
            queryset = queryset.filter(in_shopping_lists__user=user)

        return queryset

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateRecipeSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        recipe = self.get_object()
        if recipe.author != self.request.user:
            raise exceptions.PermissionDenied(
                'У вас нет прав редактировать этот рецепт.')
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        recipe = self.get_object()
        if recipe.author != request.user:
            raise exceptions.PermissionDenied(
                'У вас нет прав удалить этот рецепт.'
            )
        recipe.delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if request.method == 'DELETE':
            try:
                favorite = Favorite.objects.get(user=user, recipe=recipe)
                favorite.delete()
                return response.Response(status=status.HTTP_204_NO_CONTENT)
            except Favorite.DoesNotExist:
                return response.Response(status=status.HTTP_400_BAD_REQUEST)

        favorite, created = Favorite.objects.get_or_create(
            user=user,
            recipe=recipe
        )
        recipe_serializer = ShortRecipeSerializer(recipe)
        if created:
            return response.Response(
                recipe_serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(status=status.HTTP_400_BAD_REQUEST)

    @decorators.action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        short_link = self.generate_short_link(recipe.id)
        return response.Response(
            {"short-link": short_link}, status=status.HTTP_200_OK)

    def generate_short_link(self, recipe_id):
        hash_object = hashlib.sha256(str(recipe_id).encode())
        short_hash = hash_object.hexdigest()[:6]
        base_url = BASE_URl
        return f"{base_url}{short_hash}"

    @decorators.action(
        detail=True,
        methods=['post', 'delete'],
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'DELETE':
            subscription = ShoppingList.objects.filter(
                user=user, recipe=recipe)
            if subscription.exists():
                subscription.delete()
                return response.Response(
                    RecipeSerializer(recipe).data,
                    status=status.HTTP_204_NO_CONTENT
                )
            return response.Response(status=status.HTTP_400_BAD_REQUEST)

        if ShoppingList.objects.filter(user=user, recipe=recipe).exists():
            return response.Response(status=status.HTTP_400_BAD_REQUEST)

        ShoppingList.objects.create(user=user, recipe=recipe)
        return response.Response(
            ShortRecipeSerializer(recipe).data,
            status=status.HTTP_201_CREATED
        )

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


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    def list(self, request):
        tags = Tag.objects.all()
        serializer = TagSerializer(tags, many=True)
        return response.Response(serializer.data, status=status.HTTP_200_OK)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return response.Response(serializer.data)


class CustomUserViewSet(UserViewSet):
    serializer_class = AuthorSerializer
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = LimitPageNumberPagination

    def users_profile(self, request, id):
        try:
            user = CustomUser.objects.get(id=id)
        except CustomUser.DoesNotExist:
            return response.Response(status=status.HTTP_404_NOT_FOUND)

        serializer = AuthorSerializer(user, context={'request': request})
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(
        detail=False,
        methods=['get'],
    )
    def subscriptions(self, request):
        subscriptions = request.user.subscriptions.all()
        paginator = self.paginator
        paginated_subscriptions = paginator.paginate_queryset(
            subscriptions, request)
        recipes_limit = request.query_params.get('recipes_limit', None)
        serialized_data = []

        for subscription in paginated_subscriptions:
            author = subscription.author

            if recipes_limit is not None:
                try:
                    recipes_limit = int(recipes_limit)
                except ValueError:
                    return response.Response(
                        status=status.HTTP_400_BAD_REQUEST)
                recipes = author.recipes.all()[:recipes_limit]
            else:
                recipes = author.recipes.all()

            user_serializer = CustomUserSerializer(author, context={
                'request': request})
            user_data = user_serializer.data
            recipe_serializer = ShortRecipeSerializer(
                recipes, many=True, context={'request': request})

            user_data['recipes'] = recipe_serializer.data
            user_data['recipes_count'] = author.recipes.count()

            serialized_data.append(user_data)

        response_data = {
            "count": subscriptions.count(),
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serialized_data
        }

        return response.Response(response_data, status=status.HTTP_200_OK)

    @decorators.action(
        detail=True,
        methods=['post', 'delete'],
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(CustomUser, id=id)

        if request.user == author:
            return response.Response(status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'DELETE':
            subscription = Subscribe.objects.filter(
                user=request.user, author=author)
            if subscription.exists():
                subscription.delete()
                return response.Response(status=status.HTTP_204_NO_CONTENT)
            return response.Response(status=status.HTTP_400_BAD_REQUEST)

        if Subscribe.objects.filter(user=request.user, author=author).exists():
            return response.Response(status=status.HTTP_400_BAD_REQUEST)

        Subscribe.objects.create(user=request.user, author=author)

        recipes = author.recipes.all()
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            try:
                recipes_limit = int(recipes_limit)
            except ValueError:
                return response.Response(status=status.HTTP_400_BAD_REQUEST)
            recipes = recipes[:recipes_limit]

        recipe_serializer = ShortRecipeSerializer(
            recipes, many=True, context={'request': request})
        user_serializer = CustomUserSerializer(
            author, context={'request': request})
        user_data = user_serializer.data
        user_data['recipes'] = recipe_serializer.data

        return response.Response(user_data, status=status.HTTP_201_CREATED)

    @decorators.action(
        detail=True,
        methods=['put', 'delete'],
    )
    def avatar(self, request, id):
        if id == 'me':
            user = request.user
        else:
            user = get_object_or_404(CustomUser, id=id)

        if request.method == 'PUT':
            if 'avatar' not in request.data:
                return response.Response(
                    status=status.HTTP_400_BAD_REQUEST)
            avatar_data = request.data.get('avatar')
            data = {'avatar': avatar_data}
            serializer = AuthorSerializer(
                user,
                data=data,
                partial=True,
                context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                return response.Response(
                    serializer.data, status=status.HTTP_200_OK)
            return response.Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            user.avatar.delete()
            user.save()
            return response.Response(status=status.HTTP_204_NO_CONTENT)
