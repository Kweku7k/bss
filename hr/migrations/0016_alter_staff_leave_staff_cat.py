# Generated by Django 4.2.14 on 2025-01-04 23:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0015_alter_companyinformation_staff_cat'),
    ]

    operations = [
        migrations.AlterField(
            model_name='staff_leave',
            name='staff_cat',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Staff Category'),
        ),
    ]