from django.db import models
from django.utils import timezone

class Sensor(models.Model):
    nome = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nome

class FluxoAgua(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name="leituras")
    data_hora = models.DateTimeField(default=timezone.now)
    valor = models.DecimalField(max_digits=10, decimal_places=3)  # litros instantâneos

    def __str__(self):
        return f"{self.sensor.nome} - {self.data_hora} - {self.valor} L"

class ConsumoDiario(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name="consumos_diarios")
    data = models.DateField()
    consumo_total = models.DecimalField(max_digits=10, decimal_places=3)
    hora = models.TimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sensor", "data"], name="unique_sensor_data")
        ]

    def __str__(self):
        return f"{self.sensor.nome} - {self.data} - {self.consumo_total} L"
