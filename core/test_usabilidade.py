from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Material, Perfil, Pesagem
from .services import classificar, registrar, resumo_estoque


class UsabilidadeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('teste', password='Senha123!')
        Perfil.objects.create(usuario=self.user, cargo='diretoria')
        self.material = Material.objects.get(nome='Metal')
        self.c = self.material.classificacoes.get(nome='Cobre')
        self.client.force_login(self.user)

    def pesagem(self, mes=2, peso='10', ano=2026):
        return Pesagem.objects.create(data=date(ano, mes, 3), material=self.material, peso=Decimal(peso), usuario=self.user)

    def test_total_muda_ao_salvar_pesagem_antes_de_classificar(self):
        self.client.post(reverse('novo_estoque'), {'data': '2026-02-03', 'material': self.material.pk, 'peso': '10'})
        self.assertEqual(resumo_estoque(), {'total': 10, 'classificado': 0, 'pendente': 10})
        for pagina in ['estoque', 'painel']:
            response = self.client.get(reverse(pagina))
            self.assertEqual(response.context['saldo_total'], 10)
            self.assertContains(response, 'Peso total em estoque')
            self.assertContains(response, 'Aguardando classificação')
        response = self.client.get(reverse('classificar', args=[Pesagem.objects.get().pk]))
        self.assertContains(response, 'já estão incluídos no estoque total')

    def test_classificar_nao_duplica_total_e_venda_reduz_total(self):
        p = self.pesagem()
        classificar(p.pk, self.user, {f'peso_{self.c.pk}': Decimal('10')})
        self.assertEqual(resumo_estoque(), {'total': 10, 'classificado': 10, 'pendente': 0})
        registrar(date(2026, 2, 4), self.user, self.material, {f'peso_{self.c.pk}': Decimal('3'), f'preco_{self.c.pk}': Decimal('2')}, True)
        self.assertEqual(resumo_estoque(), {'total': 7, 'classificado': 7, 'pendente': 0})

    def test_total_respeita_material_e_nao_depende_do_periodo(self):
        self.pesagem()
        papel = Material.objects.get(nome='Papelão')
        self.assertEqual(resumo_estoque(papel.pk)['total'], 0)
        response = self.client.get(reverse('estoque'), {'material': papel.pk})
        self.assertEqual(response.context['saldo_total'], 0)
        response = self.client.get(reverse('painel'), {'ano': 2000, 'mes': 2})
        self.assertEqual(response.context['saldo_total'], 10)
        self.assertEqual(response.context['recebido'], 0)

    def test_intervalo_inclusivo_grafico_e_totais_mesmos_meses(self):
        for mes, peso in [(1, '5'), (2, '10'), (3, '15'), (4, '20')]:
            p = self.pesagem(mes, peso)
            if mes in [2, 3]:
                classificar(p.pk, self.user, {f'peso_{self.c.pk}': Decimal(peso)})
        self.pesagem(2, '999', 2025)
        registrar(date(2026, 2, 4), self.user, self.material, {f'peso_{self.c.pk}': Decimal('7')})
        for mes, peso in [(2, '3'), (3, '2'), (4, '1')]:
            registrar(date(2026, mes, 5), self.user, self.material, {f'peso_{self.c.pk}': Decimal(peso), f'preco_{self.c.pk}': Decimal('2')}, True)
        response = self.client.get(reverse('painel'), {'ano': 2026, 'mes': 2, 'mes_final': 3})
        self.assertEqual(response.context['grafico']['meses'], ['Fev', 'Mar'])
        self.assertEqual(response.context['grafico']['series'][2]['valores'], [17.0, 15.0])
        self.assertEqual(response.context['recebido'], 32)
        self.assertEqual(response.context['vendido'], 5)
        self.assertEqual(response.context['receita'], 10)
        self.assertContains(response, 'Fevereiro a Março de 2026')

    def test_um_mes_ou_ano_inteiro_continuam_funcionando(self):
        self.pesagem()
        for params in [{'ano': 2026, 'mes': 2}, {'ano': 2026, 'mes': 2, 'mes_final': 2}]:
            response = self.client.get(reverse('painel'), params)
            self.assertEqual(len(response.context['grafico']['meses']), 28)
            self.assertEqual(response.context['recebido'], 10)
        response = self.client.get(reverse('painel'), {'ano': 2026})
        self.assertEqual(len(response.context['grafico']['meses']), 12)
        self.assertEqual(response.context['recebido'], 10)

    def test_intervalo_invalido_exibe_erro_sem_grafico_enganoso(self):
        self.pesagem()
        for params in [{'ano': 2026, 'mes': 5, 'mes_final': 2}, {'ano': 2026, 'mes_final': 3}]:
            response = self.client.get(reverse('painel'), params)
            self.assertTrue(response.context['form'].errors)
            self.assertContains(response, 'Corrija o período selecionado')
            self.assertNotContains(response, '<canvas')
