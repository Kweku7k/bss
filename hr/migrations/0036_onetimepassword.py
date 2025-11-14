from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0035_payroll_is_journalized_payrolljournal_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OneTimePassword',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=6)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('is_used', models.BooleanField(default=False)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name='one_time_passwords',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
                'get_latest_by': 'created_at',
            },
        ),
        migrations.AddIndex(
            model_name='onetimepassword',
            index=models.Index(fields=['user', 'code'], name='hr_otp_user_code_idx'),
        ),
        migrations.AddIndex(
            model_name='onetimepassword',
            index=models.Index(fields=['expires_at'], name='hr_otp_expires_idx'),
        ),
    ]

