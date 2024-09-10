from django.contrib import admin

from .models import ChatHistory, Thread

# Register your models here.
admin.site.register(ChatHistory)
admin.site.register(Thread)
