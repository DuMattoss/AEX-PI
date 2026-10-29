from calendar import monthrange
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .access import exige_cargo, pode_vender, cargo
from .forms import EtapaForm, ItensForm, RelatorioForm, PesagemForm, CooperadoForm, PainelForm
from .models import Material, Classificacao, RegistroEstoque, Venda, ItemEstoque, ItemVenda, Perfil, Pesagem
from .services import registrar, saldos, ZERO, classificar, recebimentos, resumo_estoque

MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


def registros(model):
    return model.objects.prefetch_related('itens__classificacao__material')


@login_required
def menu(request):
    return render(request, 'menu.html')


@login_required
def listagem(request, venda=False):
    if venda and not pode_vender(request.user):
        raise PermissionDenied
    filtro = request.GET.get('material', '')
    if venda:
        lista = registros(Venda)
        if filtro.isdigit():
            lista = lista.filter(itens__classificacao__material_id=filtro).distinct()
    else:
        lista = []
        pesagens = Pesagem.objects.select_related('material', 'registro').prefetch_related('registro__itens__classificacao__material')
        antigos = registros(RegistroEstoque).filter(pesagem__isnull=True)
        if filtro.isdigit():
            pesagens = pesagens.filter(material_id=filtro)
            antigos = antigos.filter(itens__classificacao__material_id=filtro).distinct()
        for p in pesagens:
            lista.append({'id': p.pk, 'data': p.data, 'material': p.material, 'peso_total': p.peso, 'pendente': not p.classificada, 'itens': list(p.registro.itens.all()) if p.classificada else []})
        for r in antigos:
            lista.append({'id': r.pk, 'data': r.data, 'material': r.material, 'peso_total': r.peso_total, 'pendente': False, 'itens': list(r.itens.all())})
        lista.sort(key=lambda r: (r['data'], r['id']), reverse=True)
    saldo = saldos()
    pendentes = Pesagem.objects.filter(registro__isnull=True)
    if filtro.isdigit():
        pendentes = pendentes.filter(material_id=filtro)
    detalhes = [{'nome': c.nome, 'material': c.material.nome, 'peso': saldo[c.pk]} for c in Classificacao.objects.select_related('material') if not filtro.isdigit() or str(c.material_id) == filtro]
    por_material = []
    for m in Material.objects.all():
        if filtro.isdigit() and str(m.pk) != filtro:
            continue
        classificado = sum((s['peso'] for s in detalhes if s['material'] == m.nome), ZERO)
        pendente = pendentes.filter(material=m).aggregate(t=Sum('peso'))['t'] or ZERO
        por_material.append({'nome': m.nome, 'classificado': classificado, 'pendente': pendente, 'total': classificado + pendente})
    resumo = resumo_estoque(int(filtro) if filtro.isdigit() else None)
    return render(request, 'listagem.html', {'venda': venda, 'registros': lista, 'materiais': Material.objects.all(), 'filtro': filtro, 'resumo_estoque': resumo, 'saldo_total': resumo['total'], 'saldo_vendavel': resumo['classificado'], 'saldos': detalhes, 'por_material': por_material, 'peso_pendente': resumo['pendente']})


@login_required
def nova_pesagem(request):
    form = PesagemForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        pesagem = Pesagem.objects.create(usuario=request.user, **form.cleaned_data)
        messages.success(request, 'Pesagem registrada. Classifique o material para disponibilizá-lo para venda.')
        return redirect('classificar', pk=pesagem.pk)
    return render(request, 'formulario.html', {'form': form, 'titulo': 'Registrar pesagem', 'descricao': 'Informe a data, o tipo de material e o peso recebido na balança.', 'botao': 'Salvar pesagem e classificar', 'voltar': 'estoque'})


@login_required
def classificacao(request, pk):
    pesagem = get_object_or_404(Pesagem.objects.select_related('material'), pk=pk)
    if pesagem.classificada:
        messages.info(request, 'Esta pesagem já foi classificada.')
        return redirect('estoque')
    form = ItensForm(request.POST or None, classificacoes=pesagem.material.classificacoes.all())
    if request.method == 'POST' and form.is_valid():
        try:
            classificar(pesagem.pk, request.user, form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Material classificado e disponível para venda.')
            return redirect('estoque')
    return render(request, 'classificar.html', {'pesagem': pesagem, 'itens': form, 'resumo_estoque': resumo_estoque()})


@exige_cargo('diretoria', 'presidente')
def novo(request):
    etapa = EtapaForm(request.POST or None)
    itens = None
    material = None
    if request.method == 'POST' and etapa.is_valid():
        material = etapa.cleaned_data['material']
        itens = ItensForm(request.POST if request.POST.get('acao') in ['revisar', 'confirmar', 'corrigir'] else None, classificacoes=material.classificacoes.all(), venda=True)
        saldo = saldos()
        for row in itens.rows:
            row['saldo'] = saldo[row['classificacao'].pk]
        if request.POST.get('acao') in ['revisar', 'confirmar'] and itens.is_valid():
            try:
                if request.POST['acao'] == 'revisar':
                    resumo = registrar(etapa.cleaned_data['data'], request.user, material, itens.cleaned_data, venda=True, simular=True)
                    return render(request, 'confirmar_venda.html', {'resumo': resumo, 'etapa': etapa, 'material': material, 'itens': itens})
                registro = registrar(etapa.cleaned_data['data'], request.user, material, itens.cleaned_data, venda=True)
            except ValidationError as error:
                itens.add_error(None, error)
            else:
                messages.success(request, 'Venda registrada com sucesso. Relatório disponível abaixo.')
                return redirect('relatorio_venda', pk=registro.pk)
    return render(request, 'novo.html', {'etapa': etapa, 'itens': itens, 'material': material, 'venda': True})


@exige_cargo('diretoria', 'presidente')
def relatorio_venda(request, pk):
    venda = get_object_or_404(registros(Venda).select_related('usuario'), pk=pk)
    return render(request, 'relatorio_venda.html', {'venda': venda})


@login_required
def painel(request):
    form = PainelForm(request.GET if request.GET else None)
    ano, mes, mes_final = timezone.localdate().year, None, None
    if form.is_bound and form.is_valid():
        ano, mes, mes_final = form.cleaned_data['ano'], form.cleaned_data['mes'], form.cleaned_data['mes_final']
    pesagens, antigos = recebimentos(ano, mes, mes_final)
    mensal = bool(mes and (not mes_final or mes_final == mes))
    eixo = list(range(1, monthrange(ano, mes)[1] + 1)) if mensal else list(range(mes or 1, (mes_final or 12) + 1))
    series = []
    for material in Material.objects.all():
        dados = {i: ZERO for i in eixo}
        for p in pesagens.filter(material=material):
            dados[p.data.day if mensal else p.data.month] += p.peso
        for item in antigos.filter(classificacao__material=material).select_related('registro'):
            dados[item.registro.data.day if mensal else item.registro.data.month] += item.peso
        series.append({'nome': material.nome, 'valores': [float(dados[i]) for i in eixo]})
    filtro = {'venda__data__year': ano}
    if mes:
        filtro['venda__data__month__range'] = (mes, mes_final or mes)
    vendido = ItemVenda.objects.filter(**filtro).aggregate(t=Sum('peso'))['t'] or ZERO
    venda_qs = Venda.objects.filter(data__year=ano)
    if mes:
        venda_qs = venda_qs.filter(data__month__range=(mes, mes_final or mes))
    periodo = f'{MESES[mes - 1]} de {ano}' if mes else str(ano)
    if mes and not mensal:
        periodo = f'{MESES[mes - 1]} a {MESES[mes_final - 1]} de {ano}'
    resumo = resumo_estoque()
    return render(request, 'painel.html', {'form': form, 'ano': ano, 'periodo': periodo, 'eixo_descricao': 'Dias do mês' if mensal else 'Meses do período', 'grafico': {'meses': [f'{i:02}' for i in eixo] if mensal else [MESES[i - 1][:3] for i in eixo], 'series': series}, 'tem_dados': pesagens.exists() or antigos.exists(), 'resumo_estoque': resumo, 'saldo_total': resumo['total'], 'vendido': vendido, 'recebido': sum((p.peso for p in pesagens), ZERO) + sum((i.peso for i in antigos), ZERO), 'receita': (venda_qs.aggregate(t=Sum('valor_total'))['t'] or ZERO) if pode_vender(request.user) else None})


@login_required
def relatorios(request):
    return render(request, 'relatorios.html', {'meses': enumerate(MESES, 1), 'hoje': timezone.localdate()})


@login_required
def visualizar_relatorio(request):
    form = RelatorioForm(request.GET)
    if not form.is_valid():
        messages.error(request, 'Selecione um período válido. ' + form.errors.as_text())
        return redirect('relatorios')
    dados = form.cleaned_data
    financeiro = request.GET.get('categoria', 'producao') == 'vendas'
    if financeiro and not pode_vender(request.user):
        raise PermissionDenied
    filtro = {'data__year': dados['ano']}
    mes = dados['mes'] if dados['tipo'] == 'mensal' else None
    if mes:
        filtro['data__month'] = mes
    entradas = registros(RegistroEstoque).filter(**filtro)
    vendas = registros(Venda).filter(**filtro)
    iv = ItemVenda.objects.filter(venda__in=vendas)
    pesagens, antigos = recebimentos(dados['ano'], mes)
    materiais = []
    for m in Material.objects.all():
        materiais.append({'nome': m.nome, 'recebido': (pesagens.filter(material=m).aggregate(t=Sum('peso'))['t'] or ZERO) + (antigos.filter(classificacao__material=m).aggregate(t=Sum('peso'))['t'] or ZERO), 'vendido': iv.filter(classificacao__material=m).aggregate(t=Sum('peso'))['t'] or ZERO})
    periodo = str(dados['ano']) if not mes else f'{MESES[mes - 1]} de {dados["ano"]}'
    return render(request, 'visualizar_relatorio.html', {'tipo': dados['tipo'], 'periodo': periodo, 'entradas': entradas, 'pesagens_pendentes': pesagens.filter(registro__isnull=True), 'vendas': vendas if financeiro else None, 'materiais': materiais, 'recebido': sum((m['recebido'] for m in materiais), ZERO), 'vendido': iv.aggregate(t=Sum('peso'))['t'] or ZERO, 'financeiro': financeiro, 'tem_dados': pesagens.exists() or antigos.exists() or vendas.exists(), 'receita': (vendas.aggregate(t=Sum('valor_total'))['t'] or ZERO) if financeiro else None})


@exige_cargo('presidente')
def cooperados(request):
    usuarios = get_user_model().objects.filter(is_superuser=False).exclude(perfil__cargo='presidente').select_related('perfil').order_by('first_name', 'username')
    return render(request, 'cooperados.html', {'usuarios': usuarios})


@exige_cargo('presidente')
def editar_cooperado(request, pk=None):
    usuario = get_object_or_404(get_user_model(), pk=pk) if pk else None
    if usuario and (cargo(usuario) == 'presidente' or usuario.pk == request.user.pk):
        raise PermissionDenied
    form = CooperadoForm(request.POST, usuario=usuario) if request.method == 'POST' else CooperadoForm(usuario=usuario)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        try:
            with transaction.atomic():
                usuario = usuario or get_user_model()()
                usuario.username = data['username']
                usuario.first_name = data['nome']
                usuario.last_name = data['sobrenome']
                usuario.email = data['email']
                usuario.is_active = data['ativo']
                if data['senha']:
                    usuario.set_password(data['senha'])
                usuario.save()
                Perfil.objects.update_or_create(usuario=usuario, defaults={'cargo': data['cargo'], 'telefone': data['telefone'], 'cpf': data['cpf']})
        except IntegrityError:
            form.add_error(None, 'O cadastro já existe. Confira o login, e-mail e CPF.')
        else:
            messages.success(request, 'Cadastro atualizado.' if pk else 'Cooperado cadastrado com sucesso.')
            return redirect('cooperados')
    return render(request, 'formulario.html', {'form': form, 'titulo': 'Editar cooperado' if pk else 'Cadastrar cooperado', 'botao': 'Salvar cadastro', 'voltar': 'cooperados'})


@exige_cargo('presidente')
def excluir_cooperado(request, pk):
    usuario = get_object_or_404(get_user_model(), pk=pk)
    if cargo(usuario) == 'presidente' or usuario.pk == request.user.pk:
        raise PermissionDenied
    if request.method == 'POST':
        try:
            usuario.delete()
        except ProtectedError:
            usuario.is_active = False
            usuario.save(update_fields=['is_active'])
            messages.success(request, 'Acesso desativado. O cadastro foi preservado porque possui movimentações vinculadas.')
        else:
            messages.success(request, 'Cadastro excluído com sucesso.')
        return redirect('cooperados')
    return render(request, 'excluir_cooperado.html', {'cooperado': usuario})
