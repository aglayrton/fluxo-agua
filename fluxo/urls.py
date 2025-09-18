from django.urls import path, include
from rest_framework import routers
from .views import FluxoViewSet, ConsumoResidenciaView, ConsumoMensalView, SensorViewSet

router = routers.DefaultRouter()
router.register("sensores", SensorViewSet, basename="sensor")
router.register("fluxo", FluxoViewSet, basename="fluxo")
router.register("consumo-residencia", ConsumoResidenciaView, basename="consumo_residencia")
router.register("consumo-mensal", ConsumoMensalView, basename="consumo_mensal")

urlpatterns = [
    path("", include(router.urls)),
]
