from django.db import migrations


def alinhar(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Perfil = apps.get_model('core', 'Perfil')
    Pesagem = apps.get_model('core', 'Pesagem')
    Registro = apps.get_model('core', 'RegistroEstoque')
    for user in User.objects.all():
        cargo = 'presidente' if user.is_superuser or (user.username == 'demo' and user.first_name == 'Demonstração') else 'cooperado'
        Perfil.objects.get_or_create(usuario_id=user.pk, defaults={'cargo': cargo})
    for registro in Registro.objects.all():
        itens = list(registro.itens.select_related('classificacao'))
        materiais = {i.classificacao.material_id for i in itens}
        if len(materiais) == 1:
            Pesagem.objects.get_or_create(registro_id=registro.pk, defaults={'data': registro.data, 'usuario_id': registro.usuario_id, 'material_id': materiais.pop(), 'peso': sum(i.peso for i in itens)})


class Migration(migrations.Migration):
    dependencies = [('core', '0003_perfil_pesagem')]
    operations = [migrations.RunPython(alinhar, migrations.RunPython.noop)]
