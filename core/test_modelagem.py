from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from .models import Perfil, Pesagem, Material, RegistroEstoque, Venda
from .services import classificar, saldos, registrar


class ModelagemTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contas = {}
        for cargo in ['cooperado', 'diretoria', 'presidente']:
            usuario = get_user_model().objects.create_user(cargo, password='Senha123!')
            Perfil.objects.create(usuario=usuario, cargo=cargo)
            cls.contas[cargo] = usuario
        cls.material = Material.objects.get(nome='Metal')
        cls.c = cls.material.classificacoes.get(nome='Cobre')

    def pesagem(self):
        return Pesagem.objects.create(data=date(2026, 10, 28), material=self.material, peso=Decimal('10'), usuario=self.contas['cooperado'])

    def classificar(self, p):
        return classificar(p.pk, self.contas['cooperado'], {f'peso_{self.c.pk}': Decimal('10')})

    def cadastro(self, **kwargs):
        return {'nome': 'Pessoa', 'sobrenome': 'Teste', 'email': 'pessoa@exemplo.invalid', 'username': 'pessoa', 'cargo': 'cooperado', 'senha': 'NovaSenha123!', 'confirmar_senha': 'NovaSenha123!', 'ativo': 'on', **kwargs}

    def test_permissoes_diretas_get_post(self):
        for cargo in ['cooperado', 'diretoria']:
            self.client.force_login(self.contas[cargo])
            for nome in ['cooperados', 'novo_cooperado']:
                self.assertEqual(self.client.get(reverse(nome)).status_code, 403)
                self.assertEqual(self.client.post(reverse(nome), self.cadastro()).status_code, 403)
        self.client.force_login(self.contas['cooperado'])
        for nome in ['vendas', 'nova_venda']:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 403)
            self.assertEqual(self.client.post(reverse(nome)).status_code, 403)

    def test_menu_por_cargo(self):
        for cargo in self.contas:
            self.client.force_login(self.contas[cargo])
            response = self.client.get(reverse('menu'))
            if cargo == 'cooperado':
                self.assertNotContains(response, 'Gerenciar vendas')
                self.assertNotContains(response, 'Cadastrar cooperados')
            elif cargo == 'diretoria':
                self.assertContains(response, 'Gerenciar vendas')
                self.assertNotContains(response, 'Cadastrar cooperados')
            else:
                self.assertContains(response, 'Cadastrar cooperados')

    def test_classificar_conserva_peso_e_nao_duplica(self):
        p = self.pesagem()
        self.assertEqual(saldos()[self.c.pk], 0)
        self.classificar(p)
        self.assertEqual(saldos()[self.c.pk], 10)
        p.refresh_from_db()
        self.assertTrue(p.classificada)
        with self.assertRaises(ValidationError):
            self.classificar(p)
        self.assertEqual(RegistroEstoque.objects.count(), 1)

    def test_classificacao_exige_soma_exata(self):
        p = self.pesagem()
        for peso in ['9.99', '10.01']:
            with self.assertRaises(ValidationError):
                classificar(p.pk, self.contas['cooperado'], {f'peso_{self.c.pk}': Decimal(peso)})
        self.assertEqual(RegistroEstoque.objects.count(), 0)
        p.refresh_from_db()
        self.assertFalse(p.classificada)

    def test_pendente_nao_pode_ser_vendido(self):
        self.pesagem()
        with self.assertRaises(ValidationError):
            registrar(date(2026, 10, 28), self.contas['diretoria'], self.material, {f'peso_{self.c.pk}': Decimal('1'), f'preco_{self.c.pk}': Decimal('20')}, True)
        self.assertFalse(Venda.objects.exists())

    def test_producao_e_grafico_sem_contagem_dupla(self):
        p = self.pesagem()
        self.client.force_login(self.contas['cooperado'])
        params = {'tipo': 'mensal', 'mes': 10, 'ano': 2026}
        self.assertEqual(self.client.get(reverse('visualizar_relatorio'), params).context['recebido'], 10)
        self.classificar(p)
        self.assertEqual(self.client.get(reverse('visualizar_relatorio'), params).context['recebido'], 10)
        response = self.client.get(reverse('painel'), {'ano': 2026, 'mes': 10})
        self.assertEqual(sum(sum(s['valores']) for s in response.context['grafico']['series']), 10)
        self.assertEqual(self.client.get(reverse('painel'), {'ano': 2025}).context['recebido'], 0)

    def test_painel_filtra_mes_e_valida_periodo(self):
        self.pesagem()
        self.client.force_login(self.contas['cooperado'])
        self.assertFalse(self.client.get(reverse('painel'), {'ano': 2026, 'mes': 9}).context['tem_dados'])
        self.assertTrue(self.client.get(reverse('painel'), {'ano': 2026, 'mes': 10}).context['tem_dados'])
        invalido = self.client.get(reverse('painel'), {'ano': 'abc', 'mes': 99})
        self.assertTrue(invalido.context['form'].errors)

    def test_producao_nao_expoe_financeiro(self):
        self.classificar(self.pesagem())
        venda = registrar(date(2026, 10, 28), self.contas['diretoria'], self.material, {f'peso_{self.c.pk}': Decimal('3'), f'preco_{self.c.pk}': Decimal('20')}, True)
        self.client.force_login(self.contas['cooperado'])
        response = self.client.get(reverse('visualizar_relatorio'), {'tipo': 'anual', 'ano': 2026})
        self.assertNotContains(response, 'R$')
        self.assertIsNone(response.context['receita'])
        self.assertIsNone(response.context['vendas'])
        self.assertEqual(self.client.get(reverse('visualizar_relatorio'), {'tipo': 'anual', 'ano': 2026, 'categoria': 'vendas'}).status_code, 403)
        self.assertEqual(self.client.get(reverse('relatorio_venda', args=[venda.pk])).status_code, 403)
        self.assertNotContains(self.client.get(reverse('painel')), 'R$')

    def test_revisar_venda_nao_grava_e_confirmar_emite_relatorio(self):
        self.classificar(self.pesagem())
        self.client.force_login(self.contas['diretoria'])
        payload = {'data': '2026-10-28', 'material': self.material.pk, f'peso_{self.c.pk}': '3', f'preco_{self.c.pk}': '20', 'acao': 'revisar'}
        response = self.client.post(reverse('nova_venda'), payload)
        self.assertContains(response, 'Confirmar e registrar venda')
        self.assertEqual(Venda.objects.count(), 0)
        self.assertEqual(saldos()[self.c.pk], 10)
        payload['acao'] = 'confirmar'
        response = self.client.post(reverse('nova_venda'), payload)
        self.assertRedirects(response, reverse('relatorio_venda', args=[Venda.objects.get().pk]))
        report = self.client.get(response.url)
        self.assertContains(report, 'Cobre')
        self.assertContains(report, '60,00')
        self.assertEqual(saldos()[self.c.pk], 7)

    def test_confirmacao_revalida_saldo(self):
        self.classificar(self.pesagem())
        self.client.force_login(self.contas['diretoria'])
        payload = {'data': '2026-10-28', 'material': self.material.pk, f'peso_{self.c.pk}': '8', f'preco_{self.c.pk}': '20', 'acao': 'revisar'}
        self.client.post(reverse('nova_venda'), payload)
        registrar(date(2026, 10, 28), self.contas['diretoria'], self.material, {f'peso_{self.c.pk}': Decimal('5'), f'preco_{self.c.pk}': Decimal('20')}, True)
        payload['acao'] = 'confirmar'
        self.assertContains(self.client.post(reverse('nova_venda'), payload), 'estoque insuficiente')
        self.assertEqual(Venda.objects.count(), 1)

    def test_cadastro_consulta_edicao_exclusao(self):
        self.client.force_login(self.contas['presidente'])
        self.assertRedirects(self.client.post(reverse('novo_cooperado'), self.cadastro()), reverse('cooperados'))
        conta = get_user_model().objects.get(username='pessoa')
        self.assertTrue(conta.check_password('NovaSenha123!'))
        self.assertEqual(conta.perfil.cargo, 'cooperado')
        self.assertContains(self.client.get(reverse('cooperados')), 'pessoa@exemplo.invalid')
        dados = self.cadastro(nome='Alterado', cargo='diretoria', senha='', confirmar_senha='')
        self.assertRedirects(self.client.post(reverse('editar_cooperado', args=[conta.pk]), dados), reverse('cooperados'))
        conta.refresh_from_db()
        self.assertEqual(conta.first_name, 'Alterado')
        self.assertEqual(conta.perfil.cargo, 'diretoria')
        self.assertTrue(conta.check_password('NovaSenha123!'))
        self.client.get(reverse('excluir_cooperado', args=[conta.pk]))
        self.assertTrue(get_user_model().objects.filter(pk=conta.pk).exists())
        self.client.post(reverse('excluir_cooperado', args=[conta.pk]))
        self.assertFalse(get_user_model().objects.filter(pk=conta.pk).exists())

    def test_exclusao_preserva_movimentos_e_revoga_acesso(self):
        p = self.pesagem()
        self.client.force_login(self.contas['presidente'])
        self.client.post(reverse('excluir_cooperado', args=[p.usuario_id]))
        conta = get_user_model().objects.get(pk=p.usuario_id)
        self.assertFalse(conta.is_active)
        self.assertTrue(Pesagem.objects.filter(pk=p.pk).exists())
        self.assertFalse(self.client.login(username=conta.username, password='Senha123!'))

    def test_duplicados_senhas_e_cpf_invalidos(self):
        self.client.force_login(self.contas['presidente'])
        self.client.post(reverse('novo_cooperado'), self.cadastro())
        for patch in [{'username': 'PESSOA'}, {'username': 'outra'}, {'username': 'nova', 'email': 'nova@exemplo.invalid', 'cpf': '111.111.111-11'}, {'username': 'nova', 'email': 'nova@exemplo.invalid', 'confirmar_senha': 'diferente'}, {'username': 'nova', 'email': 'nova@exemplo.invalid', 'senha': '123', 'confirmar_senha': '123'}]:
            response = self.client.post(reverse('novo_cooperado'), self.cadastro(**patch))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.assertEqual(get_user_model().objects.filter(username='nova').count(), 0)

    def test_cargo_presidente_nao_pode_ser_injetado(self):
        self.client.force_login(self.contas['presidente'])
        response = self.client.post(reverse('novo_cooperado'), self.cadastro(cargo='presidente'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='pessoa').exists())
        self.assertEqual(self.client.post(reverse('excluir_cooperado', args=[self.contas['presidente'].pk])).status_code, 403)

    def test_dados_pessoais_nao_expostos_a_outros_cargos(self):
        self.client.force_login(self.contas['cooperado'])
        self.assertEqual(self.client.get(reverse('editar_cooperado', args=[self.contas['diretoria'].pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('excluir_cooperado', args=[self.contas['diretoria'].pk])).status_code, 403)
