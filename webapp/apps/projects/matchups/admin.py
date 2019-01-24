from django.contrib import admin

# Register your models here.

from .models import MatchupsInputs, MatchupsRun

admin.site.register(MatchupsInputs)
admin.site.register(MatchupsRun)
