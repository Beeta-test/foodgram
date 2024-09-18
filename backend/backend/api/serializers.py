import base64

from core.consts import EMAIL_LENGTH, USERNAME_LENGTH
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Tag)
from rest_framework import exceptions, serializers
from rest_framework.validators import UniqueTogetherValidator
from users.models import CustomUser, Subscribe


class CustomUserCreateSerializer(UserCreateSerializer):

    email = serializers.EmailField(
        required=True,
        max_length=EMAIL_LENGTH,
        label="Адрес электронной почты",
        help_text="string <email> <= 254 characters"
    )
    username = serializers.RegexField(
        required=True,
        max_length=USERNAME_LENGTH,
        regex=r'^[\w.@+-]+\Z',
        label="Уникальный юзернейм",
        help_text="string <= 150 characters"
    )
    first_name = serializers.CharField(
        required=True,
        max_length=USERNAME_LENGTH,
        label="Имя",
        help_text="string <= 150 characters"
    )
    last_name = serializers.CharField(
        required=True,
        max_length=USERNAME_LENGTH,
        label="Фамилия",
        help_text="string <= 150 characters"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        label="Пароль",
        help_text="Пароль"
    )

    class Meta:
        model = CustomUser
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password')

    def validate_username(self, value: str) -> str:
        if value.lower() == "me":
            raise serializers.ValidationError(
                "Использование имени 'me' в качестве username запрещено."
            )

        return value

    def validate(self, data):
        email = data.get("email")
        username = data.get("username")
        user_by_email = CustomUser.objects.filter(email=email).first()
        user_by_username = CustomUser.objects.filter(username=username).first()

        errors = {}

        if user_by_email and user_by_email.username != username:
            errors["email"] = "Поле используется другим пользователем."

        if user_by_username and user_by_username.email != email:
            errors["username"] = "Поле используется другим пользователем."

        if errors:
            raise serializers.ValidationError(errors)

        if user_by_email or user_by_username:
            data["user"] = user_by_email or user_by_username

        return data


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class AuthorSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(default=False)
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and not request.user.is_anonymous:
            return Subscribe.objects.filter(
                user=request.user, author=obj.id).exists()
        return False

    def to_representation(self, instance):
        if isinstance(instance, AnonymousUser):
            raise exceptions.AuthenticationFailed(
                detail="Пользователь не авторизован", code=401)

        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.method == 'PUT':
            return {'avatar': representation.get('avatar')}

        return representation


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    amount = serializers.FloatField()

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'measurement_unit', 'amount']


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.FloatField()

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'amount']


class ShortRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = [
            'id',
            'name',
            'image',
            'cooking_time',
        ]


class RecipeSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipeingredient_set', many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = [
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        ]

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and not request.user.is_anonymous:
            return Favorite.objects.filter(
                user=request.user, recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and not request.user.is_anonymous:
            return ShoppingList.objects.filter(
                user=request.user, recipe=obj).exists()
        return False

    def validate_image(self, value):
        if value is None or value == '':
            return None
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['image'] = self.get_image_url(instance)
        return representation

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return '/media/defaults/default_image.png'


class CreateRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True)
    ingredients = RecipeIngredientCreateSerializer(many=True)

    class Meta:
        model = Recipe
        fields = [
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        ]

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)

        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.get('id')
            amount = ingredient_data.get('amount')

            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
            )

        recipe.tags.set(tags_data)

        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time)

        image = validated_data.get('image', None)
        if image:
            instance.image = image

        tags_data = validated_data.pop('tags', [])
        instance.tags.set(tags_data)

        RecipeIngredient.objects.filter(recipe=instance).delete()

        ingredients_data = validated_data.pop('ingredients', [])
        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.get('id')
            amount = ingredient_data.get('amount')

            RecipeIngredient.objects.create(
                recipe=instance,
                ingredient=ingredient,
                amount=amount
            )

        instance.save()
        return instance

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым.")
        unique_ingredients = set()
        for ingredient in value:
            if ingredient['amount'] < 1:
                raise serializers.ValidationError(
                    (f"Количество ингредиента '{ingredient}'"
                      "должно быть не меньше 1."))
            ingredient_id = ingredient['id']
            if ingredient_id in unique_ingredients:
                raise serializers.ValidationError(
                    f"Ингредиент '{ingredient}' не должен повторяться."
                )
            unique_ingredients.add(ingredient_id)
        return value

    def validate_tags(self, value):
        unique_tags = set()
        for tag in value:
            if tag in unique_tags:
                raise serializers.ValidationError(
                    f"Тег '{tag}' не должен повторяться.")
            unique_tags.add(tag)
        return value

    def validate(self, data):
        if 'ingredients' not in data:
            raise serializers.ValidationError(
                ({"ingredients": "Поле 'ingredients'"
                  "обязательно для заполнения."}))
        if 'tags' not in data:
            raise serializers.ValidationError(
                {"tags": "Поле 'tags' обязательно для заполнения."})
        if 'image' not in data:
            raise serializers.ValidationError(
                {"image": "Поле 'image' обязательно для заполнения."})
        if 'text' not in data:
            raise serializers.ValidationError(
                {"text": "Поле 'text' обязательно для заполнения."})
        if 'cooking_time' not in data:
            raise serializers.ValidationError(
                ({"cooking_time": "Поле 'cooking_time'"
                  "обязательно для заполнения."}))
        if data.get('cooking_time', 0) < 1:
            raise serializers.ValidationError(
                ({"cooking_time": "Время приготовления должно"
                  "быть не менее 1 минуты."}))

        return data

    def to_representation(self, instance):
        serializer = RecipeSerializer(instance)
        return serializer.data


class CustomUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(default=False)
    recipes = RecipeSerializer(many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        ]

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscribe.objects.filter(user=user, author=obj).exists()

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class SubscriptionSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    author = serializers.SlugRelatedField(
        slug_field='username', queryset=CustomUser.objects.all()
    )

    class Meta:
        model = Subscribe
        fields = ('user', 'author')
        validators = [
            UniqueTogetherValidator(
                queryset=Subscribe.objects.all(),
                fields=['user', 'author'],
                message='Вы уже подписаны на этого пользователя.'
            )
        ]

    def validate_author(self, value):
        if self.context['request'].user == value:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.'
            )
        return value


class SubscriptionRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.ReadOnlyField()
    image = Base64ImageField()
    cooking_time = serializers.ReadOnlyField()

    class Meta:
        model = Recipe
        fields = [
            'id',
            'name',
            'image',
            'cooking_time'
        ]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None
