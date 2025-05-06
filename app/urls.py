from django.contrib import admin
from django.urls import path
from task.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),

    path('home/', dashboard, name='dashboard'),
]
