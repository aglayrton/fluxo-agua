from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from .models import FluxoAgua, Sensor, ConsumoDiario
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
            FluxoAgua.objects.filter(sensor_id=sensor_id).order_by("-id").first()
        )

        valor_diferenca = None

        if ultima_leitura:
            ultimo_valor = ultima_leitura.valor
            
            if valor_recebido < ultimo_valor:
                valor_diferenca = valor_recebido
            else:
                valor_diferenca = valor_recebido - ultimo_valor
        else:
            # Primeira leitura do sensor → diferença será o próprio valor
            valor_diferenca = valor_recebido

        # Cria o registro com o valor original e a diferença
        data_para_salvar = request.data.copy()
        data_para_salvar["valor"] = valor_recebido
        data_para_salvar["valor_diferenca"] = valor_diferenca

        serializer = self.get_serializer(data=data_para_salvar)
        serializer.is_valid(raise_exception=True)
        fluxo = serializer.save()

        # Garante que a data_hora seja timezone-aware
        if timezone.is_naive(fluxo.data_hora):
            fluxo.data_hora = make_aware(fluxo.data_hora)
            fluxo.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def reset_database(self, request):
        """
        Endpoint para resetar completamente o banco de dados
        Requer confirmação via parâmetro 'confirm': true
        """
        if not request.data.get('confirm'):
            return Response(
                {
                    "error": "Operação requer confirmação",
                    "message": "Envie 'confirm': true para confirmar o reset do banco",
                    "warning": "Esta operação irá deletar TODOS os dados!"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Conta registros antes de deletar
                deleted_fluxo = FluxoAgua.objects.all().count()
                deleted_consumo = ConsumoDiario.objects.all().count()
                deleted_sensor = Sensor.objects.all().count()

                # Deleta todos os registros
                FluxoAgua.objects.all().delete()
                ConsumoDiario.objects.all().delete()
                Sensor.objects.all().delete()

                return Response({
                    "success": True,
                    "message": "Banco de dados resetado com sucesso!",
                    "deleted_records": {
                        "fluxo_agua": deleted_fluxo,
                        "consumo_diario": deleted_consumo,
                        "sensores": deleted_sensor
                    }
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "error": "Erro ao resetar banco de dados",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
            consumo_total=Sum("valor_diferenca")
        )

        # Formata a resposta
        resposta = [
            {"sensor": c["sensor__nome"], "consumo": f"{c['consumo_total']:.2f}"}
            for c in consumo_por_sensor
        ]

        total_residencia = leituras.aggregate(total=Sum("valor_diferenca"))["total"] or Decimal(
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
            consumo_total=Sum("valor_diferenca")
        )

        resposta = [
            {
                "data": c["data_hora__date"].strftime("%d/%m/%Y"),
                "sensor": c["sensor__nome"],
                "consumo_total": f"{c['consumo_total']:.2f}",
            }
            for c in consumo_por_dia
        ]

        total_mes = leituras.aggregate(total=Sum("valor_diferenca"))["total"] or Decimal("0.00")

        return Response(
            {
                "consumo_por_dia": resposta,
                "total_mes": f"{total_mes:.2f}",
            }
        )
