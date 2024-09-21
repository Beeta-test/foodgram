from core.consts import BASE_NAME_LENGTH, BASE_SLUG_LEGHT, BASE_UTIL_LEGHT
from django.core import validators
from django.db import models
from users.models import CustomUser


class Ingredient(models.Model):
    name = models.CharField(
        'Название',
        max_length=BASE_NAME_LENGTH,
        unique=True
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=BASE_UTIL_LEGHT,
        unique=True
    )

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        default_related_name = 'ingredients'


class Tag(models.Model):
    name = models.CharField(
        'Название',
        max_length=BASE_NAME_LENGTH,
        unique=True
    )
    slug = models.SlugField(
        "Идентификатор",
        max_length=BASE_SLUG_LEGHT,
        help_text=(
            "Идентификатор страницы для URL; "
            "разрешены символы латиницы, "
            "цифры, дефис и подчёркивание."
        ),
        unique=True,
    )

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'
        default_related_name = 'tags'


class Recipe(models.Model):
    name = models.CharField('Название', max_length=BASE_NAME_LENGTH)
    author = models.ForeignKey(
        CustomUser,
        verbose_name='Автор',
        on_delete=models.CASCADE,
    )
    image = models.ImageField(
        'Фото',
        upload_to='recipes/images',
        null=True,
        blank=True,
        default=None,
    )
    text = models.TextField('Текст', default='Описание отсутствует')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes'
    )
    tags = models.ManyToManyField(Tag, related_name='recipes')
    cooking_time = models.PositiveIntegerField('Время приготовления')
    pub_date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.FloatField(
        validators=(
            validators.MinValueValidator(
                1, message='Минимальное количество ингредиентов 1'),),
        verbose_name='Количество',
    )

    def __str__(self):
        return f'{self.recipe} - {self.ingredient} ({self.amount})'

    class Meta:
        unique_together = ['recipe', 'ingredient']
        verbose_name = 'Количество ингредиента'
        verbose_name_plural = 'Количество ингредиентов'


class Favorite(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'recipe']
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f"{self.user.username} -> {self.recipe.name}"


class ShoppingList(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='shopping_lists'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_lists'
    )

    class Meta:
        unique_together = ['user', 'recipe']
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'
