# Generated by Django 3.2.16 on 2024-09-18 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0009_alter_recipeingredient_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='recipes/images', verbose_name='Фото'),
        ),
    ]
