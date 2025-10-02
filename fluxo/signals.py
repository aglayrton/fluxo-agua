from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum
from .models import FluxoAgua, ControleFluxo, MetaConsumo


@receiver(post_save, sender=FluxoAgua)
def verificar_consumo_e_controlar_fluxo(sender, instance, created, **kwargs):
    """
    Signal que verifica o consumo diário após cada registro de FluxoAgua.
    Se o consumo ultrapassar a meta e o desligamento automático ainda não ocorreu hoje,
    desliga o fluxo automaticamente.
    """
    if not created:
        return

    hoje = timezone.localdate()

    # Busca a meta atual (usando o método singleton)
    meta = MetaConsumo.get_meta_atual()
    if not meta:
        return  # Se não há meta configurada, não faz nada

    # Calcula o consumo total do dia
    consumo_hoje = FluxoAgua.objects.filter(
        data_hora__date=hoje
    ).aggregate(total=Sum('valor_diferenca'))['total'] or Decimal('0.00')

    # Busca ou cria o controle de fluxo do dia
    controle, created_controle = ControleFluxo.objects.get_or_create(
        data=hoje,
        defaults={'status': 'on', 'desligamento_automatico_ocorreu': False}
    )

    # Verifica se deve desligar automaticamente
    if consumo_hoje >= meta.meta_diaria_litros:
        # Só desliga se ainda não desligou automaticamente hoje
        # E se o usuário não alterou manualmente
        if not controle.desligamento_automatico_ocorreu and not controle.usuario_alterou_manualmente:
            controle.status = 'off'
            controle.desligamento_automatico_ocorreu = True
            controle.save()
