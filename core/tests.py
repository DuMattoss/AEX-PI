from datetime import date
from decimal import Decimal as D
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from .models import Material, Classificacao, RegistroEstoque, ItemEstoque, Venda, ItemVenda, Perfil, Pesagem
from .services import registrar, saldos


class CooperativaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('teste', password='Senha123!')
        Perfil.objects.create(usuario=cls.user, cargo='diretoria')
        cls.material = Material.objects.get(nome='Plástico')
        cls.c = cls.material.classificacoes.get(nome='PET Verde')
        cls.outra = cls.material.classificacoes.get(nome='PET Azul')

    def setUp(self):
        self.client.force_login(self.user)

    def entrada(self, peso='100', data=date(2026, 1, 10)):
        return registrar(data, self.user, self.material, {f'peso_{self.c.pk}': D(peso)})

    def venda(self, peso='30', preco='2'):
        return registrar(date(2026, 1, 15), self.user, self.material, {f'peso_{self.c.pk}': D(peso), f'preco_{self.c.pk}': D(preco)}, venda=True)

    def test_catalogo_completo_sem_duplicacao(self):
        self.assertEqual(Material.objects.count(), 3)
        self.assertEqual(Classificacao.objects.count(), 27)
        self.assertEqual(Classificacao.objects.filter(nome='PP Preto').count(), 1)

    def test_protecao_de_todas_rotas(self):
        self.client.logout()
        for nome in ['menu', 'estoque', 'vendas', 'novo_estoque', 'nova_venda', 'painel', 'relatorios', 'visualizar_relatorio']:
            self.assertRedirects(self.client.get(reverse(nome)), reverse('login') + '?next=' + reverse(nome), fetch_redirect_response=False)

    def test_login_incorreto_correto_logout(self):
        self.client.logout()
        response = self.client.post(reverse('login'), {'username': 'teste', 'password': 'errada'})
        self.assertContains(response, 'Login ou senha incorretos')
        self.assertRedirects(self.client.post(reverse('login'), {'username': 'teste', 'password': 'Senha123!'}), reverse('menu'))
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_csrf_obrigatorio(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('novo_estoque'), {}).status_code, 403)

    def test_entrada_duas_etapas_e_persistencia(self):
        self.assertRedirects(self.client.post(reverse('novo_estoque'), {'data': '2026-01-10', 'material': self.material.pk, 'peso': '100.50'}), reverse('classificar', args=[1]))
        p = Pesagem.objects.get()
        self.assertEqual(p.peso, D('100.50'))
        self.assertEqual(RegistroEstoque.objects.count(), 0)
        self.assertEqual(saldos()[self.c.pk], 0)
        self.assertRedirects(self.client.post(reverse('classificar', args=[p.pk]), {f'peso_{self.c.pk}': '100.50'}), reverse('estoque'))
        self.assertEqual(ItemEstoque.objects.get().peso, D('100.50'))
        self.assertEqual(saldos()[self.c.pk], D('100.50'))

    def test_entrada_vazia_negativa_invalida(self):
        for peso in ['', '-1', 'abc', 'NaN', '1.123']:
            response = self.client.post(reverse('novo_estoque'), {'data': '2026-01-10', 'material': self.material.pk, 'peso': peso})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(RegistroEstoque.objects.count(), 0)

    def test_saldo_venda_e_subtotal(self):
        self.entrada()
        venda = self.venda()
        venda.refresh_from_db()
        self.assertEqual(venda.valor_total, D('60.00'))
        self.assertEqual(venda.itens.get().subtotal, D('60.00'))
        self.assertEqual(saldos()[self.c.pk], D('70.00'))
        self.assertEqual(saldos()[self.outra.pk], 0)

    def test_venda_multiplos_itens_arredondamento(self):
        registrar(date(2026, 1, 1), self.user, self.material, {f'peso_{self.c.pk}': D('10'), f'peso_{self.outra.pk}': D('10')})
        venda = registrar(date(2026, 1, 2), self.user, self.material, {f'peso_{self.c.pk}': D('1.25'), f'preco_{self.c.pk}': D('2.50'), f'peso_{self.outra.pk}': D('2.00'), f'preco_{self.outra.pk}': D('3.00')}, True)
        self.assertEqual(venda.valor_total, D('9.13'))

    def test_venda_bloqueia_insuficiente_e_repeticao(self):
        self.entrada()
        with self.assertRaises(ValidationError):
            self.venda('101')
        self.assertEqual(Venda.objects.count(), 0)
        self.venda('100')
        with self.assertRaises(ValidationError):
            self.venda('1')
        self.assertEqual(saldos()[self.c.pk], 0)

    def test_precos_e_pesos_invalidos(self):
        self.entrada()
        for peso, preco in [('1', '0'), ('1', '-1'), ('-1', '2'), ('0', '2'), ('0.01', '0.01')]:
            with self.assertRaises(ValidationError):
                self.venda(peso, preco)
        self.assertEqual(Venda.objects.count(), 0)

    def test_transacao_nao_grava_venda_parcial(self):
        self.entrada()
        with self.assertRaises(ValidationError):
            registrar(date(2026, 1, 15), self.user, self.material, {f'peso_{self.c.pk}': D('5'), f'preco_{self.c.pk}': D('2'), f'peso_{self.outra.pk}': D('1'), f'preco_{self.outra.pk}': D('2')}, True)
        self.assertEqual(ItemVenda.objects.count(), 0)
        self.assertEqual(Venda.objects.count(), 0)
        self.assertEqual(saldos()[self.c.pk], 100)

    def test_fluxo_venda_com_erro_e_sucesso(self):
        self.entrada()
        base = {'data': '2026-01-15', 'material': self.material.pk, 'acao': 'confirmar', f'preco_{self.c.pk}': '2'}
        response = self.client.post(reverse('nova_venda'), {**base, f'peso_{self.c.pk}': '101'})
        self.assertContains(response, 'estoque insuficiente')
        self.assertRedirects(self.client.post(reverse('nova_venda'), {**base, f'peso_{self.c.pk}': '30'}), reverse('relatorio_venda', args=[1]))

    def test_listagens_filtro_e_ordem(self):
        self.entrada(data=date(2026, 1, 10))
        recente = self.entrada(data=date(2026, 2, 10))
        response = self.client.get(reverse('estoque'))
        self.assertEqual(response.context['registros'][0]['id'], recente.pk)
        self.assertEqual(len(self.client.get(reverse('estoque'), {'material': Material.objects.get(nome='Metal').pk}).context['registros']), 0)
        self.venda()
        self.assertEqual(len(self.client.get(reverse('vendas'), {'material': self.material.pk}).context['registros']), 1)

    def test_painel_vazio_e_com_dados(self):
        self.assertContains(self.client.get(reverse('painel')), 'Ainda não há dados')
        from django.utils import timezone
        self.entrada(data=timezone.localdate())
        response = self.client.get(reverse('painel'))
        self.assertTrue(response.context['tem_dados'])
        self.assertEqual(sum(response.context['grafico']['series'][0]['valores']), 100)

    def test_relatorios_mensal_anual_e_fora_periodo(self):
        self.entrada()
        self.entrada('50', date(2026, 2, 10))
        self.entrada('999', date(2025, 1, 10))
        self.venda()
        response = self.client.get(reverse('visualizar_relatorio'), {'tipo': 'mensal', 'ano': 2026, 'mes': 1, 'categoria': 'vendas'})
        self.assertEqual(response.context['recebido'], 100)
        self.assertEqual(response.context['vendido'], 30)
        self.assertEqual(response.context['receita'], 60)
        self.assertContains(response, 'Imprimir / Salvar em PDF')
        anual = self.client.get(reverse('visualizar_relatorio'), {'tipo': 'anual', 'ano': 2026})
        self.assertEqual(anual.context['recebido'], 150)
        self.assertEqual(anual.context['materiais'][0]['recebido'], 150)
        vazio = self.client.get(reverse('visualizar_relatorio'), {'tipo': 'anual', 'ano': 2000, 'categoria': 'vendas'})
        self.assertEqual(vazio.context['receita'], 0)

    def test_periodo_invalido(self):
        for params in [{}, {'tipo': 'mensal', 'ano': 2026, 'mes': 13}, {'tipo': 'anual', 'ano': 'abc'}]:
            self.assertRedirects(self.client.get(reverse('visualizar_relatorio'), params), reverse('relatorios'))

    def test_paginas_renderizam(self):
        for nome in ['menu', 'estoque', 'vendas', 'novo_estoque', 'nova_venda', 'painel', 'relatorios']:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200)

    def test_demo_idempotente(self):
        call_command('popular_demo', stdout=StringIO())
        total = (RegistroEstoque.objects.count(), Venda.objects.count(), Classificacao.objects.count())
        call_command('popular_demo', stdout=StringIO())
        self.assertEqual(total, (RegistroEstoque.objects.count(), Venda.objects.count(), Classificacao.objects.count()))
        self.assertTrue(get_user_model().objects.get(username='demo').check_password('Coopera123!'))
        self.assertTrue(all(v >= 0 for v in saldos().values()))
