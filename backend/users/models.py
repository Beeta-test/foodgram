from core.consts import EMAIL_LENGTH, USER_LENGTH
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):

    email = models.EmailField(
        max_length=EMAIL_LENGTH,
        unique=True,
    )
    first_name = models.CharField(max_length=USER_LENGTH)
    last_name = models.CharField(max_length=USER_LENGTH)
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        default=None
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self) -> str:
        return self.username


class Subscribe(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='followers',
    )

    class Meta:
        ordering = ('author',)
        verbose_name = 'Подписчик'
        verbose_name_plural = 'Подписчики'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscribers'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='prevent_self_author'
            ),
        ]

    def __str__(self):
        return f'{self.user.username} подписан на {self.author.username}'
