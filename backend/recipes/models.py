import random
import string

from django.core import validators
from django.db import models
from users.models import CustomUser

from backend.consts import (BASE_NAME_LENGTH, BASE_SLUG_LEGHT, BASE_UTIL_LEGHT,
                            SHORT_LINK, SHORT_NAME)


class Ingredient(models.Model):
    name = models.CharField(
        'Название',
        max_length=SHORT_NAME,
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=BASE_UTIL_LEGHT,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        default_related_name = 'ingredients'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient_unit'
            )
        ]

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'


class Tag(models.Model):
    name = models.CharField(
        'Название',
        max_length=BASE_SLUG_LEGHT,
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

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'
        default_related_name = 'tags'

    def __str__(self) -> str:
        return self.name


class Recipe(models.Model):
    name = models.CharField(
        'Название',
        max_length=BASE_NAME_LENGTH,
    )
    author = models.ForeignKey(
        CustomUser,
        verbose_name='Автор',
        on_delete=models.CASCADE,
    )
    image = models.ImageField(
        'Фото',
        upload_to='recipes/images',
        null=True,
        default=None,
    )
    text = models.TextField(
        'Текст',
        default='Описание отсутствует',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
    )
    tags = models.ManyToManyField(Tag, related_name='recipes')
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=[
            validators.MinValueValidator(
                1,
                message='Время приготовления не может быть меньше 1 минуты.'
            ),
            validators.MaxValueValidator(
                32000,
                message='Время приготовления не может превышать 32 000 минут.'
            )
        ]
    )
    pub_date = models.DateTimeField(auto_now_add=True)
    short_link = models.CharField(
        'Короткая ссылка',
        max_length=SHORT_NAME,)

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'

    def __str__(self) -> str:
        return self.name

    def get_short_link(self):
        letters = string.ascii_uppercase
        rand_string = ''.join(
            random.choice(letters) for i in range(
                SHORT_LINK))
        return rand_string

    def save(self, *args, **kwargs):
        if not self.short_link:
            self.short_link = self.get_short_link()
        return super().save(*args, **kwargs)


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.PositiveSmallIntegerField(
        'Количество',
        validators=(
            validators.MinValueValidator(
                1, message='Минимальное количество ингредиентов 1'),
            validators.MaxValueValidator(
                32000,
                message='Максимальное количество ингредиентов 32 000.')
        )
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]
        verbose_name = 'Количество ингредиента'
        verbose_name_plural = 'Количество ингредиентов'

    def __str__(self):
        return f'{self.recipe} - {self.ingredient} ({self.amount})'


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
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]
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
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_list'
            )
        ]
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'
