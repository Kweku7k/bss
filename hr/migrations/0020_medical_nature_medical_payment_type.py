# Generated by Django 4.2.14 on 2025-01-15 19:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0019_choicesmedicaltreatment'),
    ]

    operations = [
        migrations.AddField(
            model_name='medical',
            name='nature',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Nature of Treatment'),
        ),
        migrations.AddField(
            model_name='medical',
            name='payment_type',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Payment Type'),
        ),
    ]