# Generated by Django 4.2.14 on 2024-12-16 19:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('leave', '0002_alter_academicyear_academic_year'),
        ('setup', '0005_alter_bankbranch_branch_location'),
    ]

    operations = [
        migrations.CreateModel(
            name='MedicalEntitlement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entitlement', models.IntegerField()),
                ('academic_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='leave.academicyear')),
                ('staff_cat', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='setup.staffcategory')),
            ],
        ),
    ]