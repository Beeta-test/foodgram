# Generated by Django 3.2.16 on 2024-09-16 16:51

import django.core.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recipes', '0007_auto_20240916_1354'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ingredient',
            options={'default_related_name': 'ingredients', 'verbose_name': 'Ингредиент', 'verbose_name_plural': 'Ингредиенты'},
        ),
        migrations.AlterModelOptions(
            name='recipeingredient',
            options={'verbose_name': 'Количество ингредиента', 'verbose_name_plural': 'Количество ингредиентов'},
        ),
        migrations.RenameField(
            model_name='favorite',
            old_name='recipes',
            new_name='recipe',
        ),
        migrations.RenameField(
            model_name='favorite',
            old_name='users',
            new_name='user',
        ),
        migrations.RenameField(
            model_name='recipeingredient',
            old_name='ingredients',
            new_name='ingredient',
        ),
        migrations.RenameField(
            model_name='recipeingredient',
            old_name='recipes',
            new_name='recipe',
        ),
        migrations.RenameField(
            model_name='shoppinglist',
            old_name='recipes',
            new_name='recipe',
        ),
        migrations.RenameField(
            model_name='shoppinglist',
            old_name='users',
            new_name='user',
        ),
        migrations.AlterField(
            model_name='recipe',
            name='text',
            field=models.TextField(default='Описание отсутствует', verbose_name='Текст'),
        ),
        migrations.AlterField(
            model_name='recipeingredient',
            name='amount',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(1, message='Минимальное количество ингредиентов 1')], verbose_name='Количество'),
        ),
        migrations.AlterUniqueTogether(
            name='favorite',
            unique_together={('user', 'recipe')},
        ),
        migrations.AlterUniqueTogether(
            name='recipeingredient',
            unique_together={('recipe', 'ingredient', 'amount')},
        ),
        migrations.AlterUniqueTogether(
            name='shoppinglist',
            unique_together={('user', 'recipe')},
        ),
    ]
