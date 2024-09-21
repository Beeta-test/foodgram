import django_filters
from django_filters import rest_framework as filters
from recipes.models import Ingredient, Recipe, Tag
from users.models import CustomUser


class RecipeFilter(django_filters.FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug',
        conjoined=False
    )
    author = django_filters.ModelChoiceFilter(
        queryset=CustomUser.objects.all())

    class Meta:
        model = Recipe
        fields = ['author', 'tags']


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ['name']
