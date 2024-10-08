from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CustomUserViewSet, IngredientViewSet, RecipeViewSet,
                    TagViewSet)

router = DefaultRouter()

router.register(
    'recipes',
    RecipeViewSet,
    basename='recipes'
)
router.register(
    'tags',
    TagViewSet,
    basename='tags'
)
router.register(
    'ingredients',
    IngredientViewSet,
    basename="ingredients"
)

router.register(
    'users',
    CustomUserViewSet,
    basename='users'
)

urlpatterns = [
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
