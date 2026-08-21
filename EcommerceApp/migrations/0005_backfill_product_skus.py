from django.db import migrations


def backfill_skus(apps, schema_editor):
    Product = apps.get_model('EcommerceApp', 'Product')
    for product in Product.objects.filter(sku__isnull=True):
        product.sku = f'AGB-LEGACY-{product.pk:06d}'
        product.save(update_fields=['sku'])
    for product in Product.objects.filter(sku=''):
        product.sku = f'AGB-LEGACY-{product.pk:06d}'
        product.save(update_fields=['sku'])


class Migration(migrations.Migration):
    dependencies = [('EcommerceApp', '0004_default_nationwide_shipping_rate')]
    operations = [migrations.RunPython(backfill_skus, migrations.RunPython.noop)]
