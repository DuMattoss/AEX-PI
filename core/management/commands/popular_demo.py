from datetime import date
from decimal import Decimal
from importlib import import_module
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import Material, Classificacao, Perfil, Pesagem
from core.services import registrar


class Command(BaseCommand):
    help = 'Cria dados fictícios de demonstração uma única vez, sem duplicar movimentos.'

    @transaction.atomic
    def handle(self, *args, **options):
        catalogo = import_module('core.migrations.0002_catalogo').CATALOGO
        for nome, nomes in catalogo.items():
            material, _ = Material.objects.get_or_create(nome=nome)
            for c in nomes:
                Classificacao.objects.get_or_create(material=material, nome=c)
        User = get_user_model()
        for login, cargo in [('cooperado', 'cooperado'), ('diretoria', 'diretoria')]:
            conta = User.objects.filter(username=login).first()
            if conta and conta.first_name != 'Demonstração':
                raise CommandError(f'O login {login} já existe fora da demonstração. Nenhum dado alterado.')
            if not conta:
                conta = User.objects.create_user(username=login, password='Coopera123!', first_name='Demonstração', last_name=cargo.capitalize(), email=f'{login}@exemplo.invalid')
            Perfil.objects.update_or_create(usuario=conta, defaults={'cargo': cargo})
        existente = User.objects.filter(username='demo').first()
        if existente:
            if existente.first_name != 'Demonstração':
                raise CommandError('O usuário demo já existe e não pertence à demonstração. Nenhum dado alterado.')
            Perfil.objects.update_or_create(usuario=existente, defaults={'cargo': 'presidente'})
            self.stdout.write('Demonstração já criada. Contas por cargo disponíveis; nenhum movimento duplicado.')
            return
        user = User.objects.create_user(username='demo', password='Coopera123!', first_name='Demonstração')
        Perfil.objects.create(usuario=user, cargo='presidente')
        ano = timezone.localdate().year
        for mes in range(1, timezone.localdate().month + 1):
            for indice, material in enumerate(Material.objects.all()):
                classes = list(material.classificacoes.all())[:3]
                pesos = {f'peso_{c.pk}': Decimal(70 + mes * 9 + indice * 13 + j * 11) for j, c in enumerate(classes)}
                registro = registrar(date(ano, mes, 3), user, material, pesos)
                Pesagem.objects.create(data=registro.data, material=material, peso=sum(pesos.values()), usuario=user, registro=registro)
                venda = {}
                for j, c in enumerate(classes):
                    venda[f'peso_{c.pk}'] = Decimal(18 + mes * 2 + j * 3)
                    venda[f'preco_{c.pk}'] = Decimal('1.20') + Decimal(indice) + Decimal(j) / 10
                registrar(date(ano, mes, 10), user, material, venda, venda=True)
        self.stdout.write(self.style.SUCCESS('Dados FICTÍCIOS criados. Login: demo | Senha: Coopera123!'))
