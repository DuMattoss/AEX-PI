from django.db import migrations

CATALOGO = {
    'Plástico': ['Aparas Mista', 'Aparas Preta', 'Aparas Cristal', 'Aparas Branco', 'PET Verde', 'PET Óleo', 'PET Colorido', 'PET Azul', 'PEAD Branco', 'PEAD Colorido', 'PP Branco', 'PP Preto', 'PP Colorido', 'PET Bandeja', 'PS Copinho', 'PVC Rígido'],
    'Papelão': ['Papelão', 'Papel Misto', 'Papel Branco', 'Tetra Pak', 'Rafia'],
    'Metal': ['Panela', 'INOX-Ferroso', 'INOX-Bom', 'Metal', 'Cobre', 'Bloco'],
}


def popular(apps, schema_editor):
    Material = apps.get_model('core', 'Material')
    Classificacao = apps.get_model('core', 'Classificacao')
    for nome, classes in CATALOGO.items():
        material, _ = Material.objects.get_or_create(nome=nome)
        for c in classes:
            Classificacao.objects.get_or_create(material=material, nome=c)


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]
    operations = [migrations.RunPython(popular, migrations.RunPython.noop)]
