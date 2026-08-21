from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('EcommerceApp', '0005_backfill_product_skus')]

    operations = [
        migrations.CreateModel(
            name='SavedPaymentMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(default='paystack', max_length=32)),
                ('authorization_code', models.CharField(max_length=128)),
                ('signature', models.CharField(max_length=128)),
                ('brand', models.CharField(blank=True, max_length=80)),
                ('bank', models.CharField(blank=True, max_length=100)),
                ('last4', models.CharField(max_length=4)),
                ('exp_month', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('exp_year', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_payment_methods', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='savedpaymentmethod',
            constraint=models.UniqueConstraint(fields=('user', 'provider', 'signature'), name='unique_user_payment_signature'),
        ),
    ]
