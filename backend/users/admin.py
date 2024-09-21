from django.contrib import admin

from .models import CustomUser, Subscribe


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name')
    search_fields = ('email', 'username')


class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    search_fields = ('user', 'author')


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Subscribe, SubscribeAdmin)
