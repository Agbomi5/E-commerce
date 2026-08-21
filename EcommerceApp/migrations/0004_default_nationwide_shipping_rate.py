from decimal import Decimal

from django.db import migrations


def add_default_rate(apps, schema_editor):
    ShippingRate = apps.get_model('EcommerceApp', 'ShippingRate')
    if not ShippingRate.objects.exists():
        ShippingRate.objects.create(
            name='Standard nationwide delivery',
            state='',
            amount=Decimal('1500.00'),
            is_active=True,
        )


class Migration(migrations.Migration):
    dependencies = [('EcommerceApp', '0003_coupon_shippingrate_alter_review_unique_together_and_more')]
    operations = [migrations.RunPython(add_default_rate, migrations.RunPython.noop)]
