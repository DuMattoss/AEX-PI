from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from .models import Classificacao, ItemEstoque, ItemVenda, RegistroEstoque, Venda, Pesagem

ZERO = Decimal('0.00')


def saldos():
    entradas = dict(ItemEstoque.objects.values('classificacao_id').annotate(total=Sum('peso')).values_list('classificacao_id', 'total'))
    vendas = dict(ItemVenda.objects.values('classificacao_id').annotate(total=Sum('peso')).values_list('classificacao_id', 'total'))
    return {c.pk: entradas.get(c.pk, ZERO) - vendas.get(c.pk, ZERO) for c in Classificacao.objects.all()}


def resumo_estoque(material_id=None):
    """Saldo físico inclui pesagens pendentes; só o classificado está liberado para venda."""
    classes = Classificacao.objects.all()
    pendentes = Pesagem.objects.filter(registro__isnull=True)
    if material_id is not None:
        classes = classes.filter(material_id=material_id)
        pendentes = pendentes.filter(material_id=material_id)
    disponivel = saldos()
    classificado = sum((disponivel[c.pk] for c in classes), ZERO)
    pendente = pendentes.aggregate(total=Sum('peso'))['total'] or ZERO
    return {'total': classificado + pendente, 'classificado': classificado, 'pendente': pendente}


@transaction.atomic
def registrar(data, usuario, material, valores, venda=False, simular=False):
    # IMMEDIATE em SQLite serializa os escritores antes da consulta de saldo.
    classes = list(material.classificacoes.all())
    disponivel = saldos() if venda else {}
    itens = []
    for c in classes:
        peso = valores.get(f'peso_{c.pk}') or ZERO
        preco = valores.get(f'preco_{c.pk}') or ZERO
        if not peso.is_finite() or not preco.is_finite() or peso < 0 or preco < 0:
            raise ValidationError('Pesos e preços devem ser números válidos e não negativos.')
        if peso == 0:
            continue
        if venda and preco <= 0:
            raise ValidationError(f'{c.nome}: informe um preço por kg maior que zero.')
        if venda and peso > disponivel[c.pk]:
            raise ValidationError(f'{c.nome}: estoque insuficiente. Disponível: {disponivel[c.pk]:.2f} kg.')
        subtotal = (peso * preco).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        if venda and subtotal <= 0:
            raise ValidationError(f'{c.nome}: o valor do item deve ser pelo menos R$ 0,01.')
        itens.append((c, peso, preco, subtotal))
    if not itens:
        raise ValidationError('Informe pelo menos um peso positivo.')
    if simular:
        return {'itens': [{'classificacao': c, 'peso': p, 'preco': pr, 'subtotal': s} for c, p, pr, s in itens], 'peso_total': sum((i[1] for i in itens), ZERO), 'valor_total': sum((i[3] for i in itens), ZERO)}
    if venda:
        registro = Venda.objects.create(data=data, usuario=usuario, valor_total=sum((i[3] for i in itens), ZERO))
        ItemVenda.objects.bulk_create([ItemVenda(venda=registro, classificacao=c, peso=p, preco_por_kg=pr, subtotal=s) for c, p, pr, s in itens])
    else:
        registro = RegistroEstoque.objects.create(data=data, usuario=usuario)
        ItemEstoque.objects.bulk_create([ItemEstoque(registro=registro, classificacao=c, peso=p) for c, p, _, _ in itens])
    return registro


@transaction.atomic
def classificar(pesagem_id, usuario, valores):
    pesagem = Pesagem.objects.select_for_update().select_related('material').get(pk=pesagem_id)
    if pesagem.classificada:
        raise ValidationError('Esta pesagem já foi classificada.')
    total = sum((valores.get(f'peso_{c.pk}') or ZERO for c in pesagem.material.classificacoes.all()), ZERO)
    if total != pesagem.peso:
        raise ValidationError(f'A soma das classificações deve ser igual ao peso recebido: {pesagem.peso:.2f} kg. Informado: {total:.2f} kg.')
    registro = registrar(pesagem.data, usuario, pesagem.material, valores)
    pesagem.registro = registro
    pesagem.save(update_fields=['registro'])
    return registro


def recebimentos(ano=None, mes=None, mes_final=None):
    """Pesagens mais entradas antigas sem pesagem; nunca conta o mesmo peso duas vezes."""
    pesagens = Pesagem.objects.select_related('material')
    antigos = ItemEstoque.objects.filter(registro__pesagem__isnull=True).select_related('classificacao__material')
    if ano:
        pesagens = pesagens.filter(data__year=ano)
        antigos = antigos.filter(registro__data__year=ano)
    if mes:
        pesagens = pesagens.filter(data__month__range=(mes, mes_final or mes))
        antigos = antigos.filter(registro__data__month__range=(mes, mes_final or mes))
    return pesagens, antigos
