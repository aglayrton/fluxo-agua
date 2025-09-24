from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from .models import FluxoAgua, Sensor
from .serializers import FluxoAguaSerializer, SensorSerializer


class SensorViewSet(ModelViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer


class FluxoViewSet(ModelViewSet):
    serializer_class = FluxoAguaSerializer
    queryset = FluxoAgua.objects.all().order_by("-id")
    

    def create(self, request, *args, **kwargs):
        sensor_id = request.data.get("sensor")
        valor_str = request.data.get("valor")

        # Trata string convertendo vírgula para ponto se necessário
        if isinstance(valor_str, str):
            valor_str = valor_str.strip().replace(',', '.')

        valor_recebido = Decimal(valor_str)

        # Busca última leitura do sensor
        ultima_leitura = (
            FluxoAgua.objects.filter(sensor_id=sensor_id).order_by("-data_hora").first()
        )

        incremento = None

        if ultima_leitura:
            ultimo_valor = ultima_leitura.valor

            if valor_recebido == ultimo_valor:
                # Igual → ignora
                return Response(
                    {"detail": "Valor repetido, leitura ignorada."},
                    status=status.HTTP_200_OK,
                )

            elif valor_recebido > ultimo_valor:
                # Incremento normal
                incremento = valor_recebido - ultimo_valor

            else:
                # Reset detectado
                incremento = valor_recebido

        else:
            # Primeira leitura do sensor → considera o valor recebido como incremento
            incremento = valor_recebido

        # Cria o registro com o incremento (não o valor bruto do sensor)
        data_para_salvar = request.data.copy()
        data_para_salvar["valor"] = incremento

        serializer = self.get_serializer(data=data_para_salvar)
        serializer.is_valid(raise_exception=True)
        fluxo = serializer.save()

        # Garante que a data_hora seja timezone-aware
        if timezone.is_naive(fluxo.data_hora):
            fluxo.data_hora = make_aware(fluxo.data_hora)
            fluxo.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConsumoResidenciaView(ViewSet):
    """
    Retorna consumo diário e total da residência
    """

    def list(self, request):
        hoje = timezone.localdate()
        # Consulta todas as leituras do dia
        leituras = FluxoAgua.objects.filter(data_hora__date=hoje)

        # Agrega consumo por sensor
        consumo_por_sensor = leituras.values("sensor__nome").annotate(
            consumo_total=Sum("valor")
        )

        # Formata a resposta
        resposta = [
            {"sensor": c["sensor__nome"], "consumo": f"{c['consumo_total']:.2f}"}
            for c in consumo_por_sensor
        ]

        total_residencia = leituras.aggregate(total=Sum("valor"))["total"] or Decimal(
            "0.00"
        )

        return Response(
            {
                "data": hoje.strftime("%d/%m/%Y"),
                "sensores": resposta,
                "total_residencia": f"{total_residencia:.2f}",
            }
        )


class ConsumoMensalView(ViewSet):
    """
    Retorna consumo diário de um mês e total do mês
    """

    def list(self, request, ano=None, mes=None):
        if ano is None or mes is None:
            hoje = timezone.localdate()
            ano = hoje.year
            mes = hoje.month

        leituras = FluxoAgua.objects.filter(data_hora__year=ano, data_hora__month=mes)

        # Agrupa consumo por dia e sensor
        consumo_por_dia = leituras.values("data_hora__date", "sensor__nome").annotate(
            consumo_total=Sum("valor")
        )

        resposta = [
            {
                "data": c["data_hora__date"].strftime("%d/%m/%Y"),
                "sensor": c["sensor__nome"],
                "consumo_total": f"{c['consumo_total']:.2f}",
            }
            for c in consumo_por_dia
        ]

        total_mes = leituras.aggregate(total=Sum("valor"))["total"] or Decimal("0.00")

        return Response(
            {
                "consumo_por_dia": resposta,
                "total_mes": f"{total_mes:.2f}",
            }
        )
