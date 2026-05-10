from django.contrib import admin
from .models import Request

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner_number', 'title', 'status', 'urgency', 'created_by', 'created_at')
    list_filter = ('status', 'urgency', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('owner_number', 'created_at', 'updated_at')