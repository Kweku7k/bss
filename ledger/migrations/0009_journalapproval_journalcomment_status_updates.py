from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0008_journalline_date'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='journal',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='journal',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_journals', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='journal',
            name='submitted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='journal',
            name='submitted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submitted_journals', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='journal',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('PENDING_APPROVAL', 'Pending Approval'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('POSTED', 'Posted'), ('CANCELLED', 'Cancelled')], default='DRAFT', max_length=20),
        ),
        migrations.CreateModel(
            name='JournalApproval',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('SUBMITTED', 'Submitted'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('POSTED', 'Posted')], max_length=20)),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('journal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approvals', to='ledger.journal')),
            ],
            options={
                'ordering': ['created_at'],
                'verbose_name': 'Journal Approval',
                'verbose_name_plural': 'Journal Approvals',
            },
        ),
        migrations.CreateModel(
            name='JournalComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.TextField()),
                ('is_system', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('journal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='ledger.journal')),
            ],
            options={
                'ordering': ['created_at'],
                'verbose_name': 'Journal Comment',
                'verbose_name_plural': 'Journal Comments',
            },
        ),
    ]

