from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Tag)
from rest_framework import serializers
from users.models import CustomUser, Subscribe


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
            'avatar',
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return (
            bool(request)
            and request.user.is_authenticated
            and Subscribe.objects.filter(
                user=request.user, author=obj.id).exists()
        )

    def validate_avatar(self, avatar):
        if not avatar:
            raise serializers.ValidationError('Поле аватара обязательно.')
        return avatar

    def validate(self, attrs):
        request = self.context.get('request')
        if request.user.is_anonymous:
            raise serializers.ValidationError('Вы должны войти в систему.')
        return attrs


class UserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        fields = ('avatar',)
        model = CustomUser

    def validate(self, data):

        if 'avatar' not in data:
            raise serializers.ValidationError(
                'необходимо передать значение аватара')
        return data


class UserSerializer(AuthorSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = self.context.get('recipes_limit')

        recipes = obj.recipes.all()
        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
            except ValueError:
                recipes_limit = None

        if recipes_limit is not None:
            recipes = recipes[:recipes_limit]

        return ShortRecipeSerializer(
            recipes, many=True, context={'request': request}).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class SubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscribe
        fields = ['user', 'author']
        read_only_fields = ['user']

    def validate(self, attrs):
        user = self.context['request'].user
        author = attrs['author']

        if user == author:
            raise serializers.ValidationError(
                "Вы не можете подписаться на себя.")

        if Subscribe.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                "Вы уже подписаны на этого автора.")

        return attrs

    def to_representation(self, instance):
        user_data = UserSerializer(instance.author, context=self.context).data
        user_data['recipes'] = ShortRecipeSerializer(
            instance.author.recipes.all(),
            many=True,
            context={
                'request': self.context['request'],
                'recipes_limit': self.context.get('recipes_limit')
            }
        ).data
        return user_data


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

    def validate_amount(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Количество ингредиента должно быть не меньше 1.')
        return value


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

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
    image = Base64ImageField()

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

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return ''

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return (
            bool(request)
            and request.user.is_authenticated
            and Favorite.objects.filter(
                user=request.user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (
            bool(request)
            and request.user.is_authenticated
            and ShoppingList.objects.filter(
                user=request.user, recipe=obj).exists()
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['image'] = self.get_image_url(instance)
        return representation


class CreateRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True, allow_null=True)
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
        extra_kwargs = {
            'image': {'required': True},
            'name': {'required': True},
            'text': {'required': True},
            'cooking_time': {'required': True},
        }

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(
            **validated_data,
            author=self.context.get('request').user,
        )
        recipe.tags.set(tags_data)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags')
        instance.tags.set(tags_data)

        ingredients_data = validated_data.pop('ingredients')
        instance.ingredients.clear()
        self.create_ingredients(instance, ingredients_data)

        return super().update(instance, validated_data)

    def create_ingredients(self, recipe, ingredients_data):
        ingredient_list = []
        for ingredient in ingredients_data:
            recipe_ingredient_item = RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount'])
            ingredient_list.append(recipe_ingredient_item)
        RecipeIngredient.objects.bulk_create(ingredient_list)

    def validate_image(self, value):
        if value is None:
            raise serializers.ValidationError(
                'Поле "image" обязательно для заполнения.'
            )
        return value

    def validate(self, attrs):
        ingredients = attrs.get('ingredients', [])
        tags = attrs.get('tags', [])

        if not ingredients:
            raise serializers.ValidationError(
                'Список ингредиентов не может быть пустым.')
        ingredient_ids = set(ingredient['id'] for ingredient in ingredients)
        if len(ingredient_ids) != len(ingredients):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.')

        if not tags:
            raise serializers.ValidationError(
                'Список тегов не может быть пустым.')
        tag_ids = set(tag for tag in tags)
        if len(tag_ids) != len(tags):
            raise serializers.ValidationError(
                'Теги не должны повторяться.')

        return attrs

    def to_representation(self, instance):
        serializer = RecipeSerializer(instance)
        return serializer.data


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ['user', 'recipe']

    def validate(self, data):
        if Favorite.objects.filter(
            user=data['user'], recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError("Этот рецепт уже в избранном.")
        return data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingList
        fields = ['user', 'recipe']

    def validate(self, data):
        if ShoppingList.objects.filter(
            user=data['user'], recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError("Этот рецепт уже в корзине.")
        return data


class RecipeResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'text', 'cooking_time']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['is_favorited'] = Favorite.objects.filter(
            user=self.context['request'].user, recipe=instance
        ).exists()
        representation['is_in_shopping_cart'] = ShoppingList.objects.filter(
            user=self.context['request'].user, recipe=instance
        ).exists()
        return representation
