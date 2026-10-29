from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Q


class Perfil(models.Model):
    class Cargo(models.TextChoices):
        COOPERADO = 'cooperado', 'Cooperado'
        DIRETORIA = 'diretoria', 'Diretoria'
        PRESIDENTE = 'presidente', 'Presidente'

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    cargo = models.CharField(max_length=12, choices=Cargo.choices, default=Cargo.COOPERADO)
    cpf = models.CharField(max_length=11, unique=True, null=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f'{self.usuario.get_full_name() or self.usuario.username} — {self.get_cargo_display()}'


class Material(models.Model):
    nome = models.CharField(max_length=40, unique=True)

    class Meta:
        ordering = ['id']
        verbose_name_plural = 'materiais'

    def __str__(self):
        return self.nome


class Classificacao(models.Model):
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name='classificacoes')
    nome = models.CharField(max_length=60)

    class Meta:
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['material', 'nome'], name='classificacao_unica')]
        verbose_name_plural = 'classificações'

    def __str__(self):
        return f'{self.material}: {self.nome}'


class RegistroEstoque(models.Model):
    data = models.DateField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-data', '-id']

    @property
    def peso_total(self):
        return sum((item.peso for item in self.itens.all()), Decimal('0'))

    @property
    def material(self):
        item = next(iter(self.itens.all()), None)
        return item.classificacao.material if item else '—'


class ItemEstoque(models.Model):
    registro = models.ForeignKey(RegistroEstoque, on_delete=models.CASCADE, related_name='itens')
    classificacao = models.ForeignKey(Classificacao, on_delete=models.PROTECT, related_name='entradas')
    peso = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(peso__gt=0), name='entrada_peso_positivo'), models.UniqueConstraint(fields=['registro', 'classificacao'], name='entrada_item_unico')]


class Venda(models.Model):
    data = models.DateField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    valor_total = models.DecimalField(max_digits=24, decimal_places=2)

    class Meta:
        ordering = ['-data', '-id']
        constraints = [models.CheckConstraint(condition=Q(valor_total__gt=0), name='venda_total_positivo')]

    @property
    def peso_total(self):
        return sum((item.peso for item in self.itens.all()), Decimal('0'))

    @property
    def material(self):
        item = next(iter(self.itens.all()), None)
        return item.classificacao.material if item else '—'


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    classificacao = models.ForeignKey(Classificacao, on_delete=models.PROTECT, related_name='saidas')
    peso = models.DecimalField(max_digits=12, decimal_places=2)
    preco_por_kg = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=24, decimal_places=2)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(peso__gt=0) & Q(preco_por_kg__gt=0) & Q(subtotal__gt=0), name='venda_item_positivo'), models.UniqueConstraint(fields=['venda', 'classificacao'], name='venda_item_unico')]


class Pesagem(models.Model):
    data = models.DateField()
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name='pesagens')
    peso = models.DecimalField(max_digits=12, decimal_places=2)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    registro = models.OneToOneField(RegistroEstoque, on_delete=models.PROTECT, null=True, blank=True, related_name='pesagem')

    class Meta:
        ordering = ['-data', '-id']
        constraints = [models.CheckConstraint(condition=Q(peso__gt=0), name='pesagem_peso_positivo')]

    @property
    def classificada(self):
        return self.registro_id is not None
