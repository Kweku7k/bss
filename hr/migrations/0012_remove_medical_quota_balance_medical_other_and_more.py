# Generated by Django 4.2.14 on 2024-12-16 22:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0011_medical_academic_year_medical_staff_cat_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='medical',
            name='quota_balance',
        ),
        migrations.AddField(
            model_name='medical',
            name='other',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='medical',
            name='relationship',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='medical',
            name='treatment_cost',
            field=models.DecimalField(decimal_places=3, max_digits=10),
        ),
    ]