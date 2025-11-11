# Generated manually to fix IntegrityError

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_carga_categorias_deficiencia'),
    ]

    operations = [
        migrations.AlterField(
            model_name='empresa',
            name='site',
            field=models.URLField(blank=True, null=True),
        ),
    ]
