from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    return JsonResponse({"status": "ok", "service": "django-control-plane"})

urlpatterns = [
    path("health/", health),
    path("admin/", admin.site.urls),
    path("api/v1/", include("maritime.urls")),
]
