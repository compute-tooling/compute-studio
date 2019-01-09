from django.contrib import admin

# Register your models here.

from .models import CompbaseballInputs, CompbaseballRun

admin.site.register(CompbaseballInputs)
admin.site.register(CompbaseballRun)