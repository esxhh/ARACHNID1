from django.urls import path

from .views import spills_api, vessels_api

urlpatterns = [
    path("vessels/", vessels_api, name="vessels-api"),
    path("spills/", spills_api, name="spills-api"),
]
