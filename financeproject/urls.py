from django.contrib import admin 
from django.urls import path, include 

urlpatterns = [
    path('expenseapp/', include("expenseapp.urls")),
    path('admin/', admin.site.urls),
]
