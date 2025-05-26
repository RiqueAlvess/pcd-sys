from django.db import migrations

def criar_categorias(apps, schema_editor):
    CategoriaDeficiencia = apps.get_model('core', 'CategoriaDeficiencia')
    categorias = [
        "Deficiência Físico/Motora",
        "Deficiência Auditiva",
        "Deficiência Visual",
        "Deficiência Intelectual/Psicossocial",
        "Deficiência Múltipla",
    ]
    for nome in categorias:
        CategoriaDeficiencia.objects.get_or_create(nome=nome)

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),  
    ]

    operations = [
        migrations.RunPython(criar_categorias, migrations.RunPython.noop),
    ]
