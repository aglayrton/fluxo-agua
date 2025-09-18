from rest_framework import serializers
from .models import FluxoAgua, ConsumoDiario, Sensor

class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = "__all__"

class FluxoAguaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FluxoAgua
        fields = "__all__"

class ConsumoDiarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsumoDiario
        fields = "__all__"
