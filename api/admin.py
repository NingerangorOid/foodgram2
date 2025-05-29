from django.contrib import admin
from .models import User  # или User, если используете встроенную модель

admin.site.register(User)