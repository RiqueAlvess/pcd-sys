# Generated manually on 2025-11-11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("userpcd", "0002_conversa_mensagem"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mensagem",
            name="conteudo",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="mensagem",
            name="arquivo",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="chat/arquivos/",
                help_text="Arquivo anexado (PDF, imagem, etc)",
            ),
        ),
    ]
