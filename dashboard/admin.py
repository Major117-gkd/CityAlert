from django.contrib import admin
from .models import Incident

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'user_name', 'status', 'severity', 'timestamp')
    list_filter = ('category', 'status', 'severity')
    search_fields = ('user_name', 'address', 'technician')
    ordering = ('-timestamp',)
