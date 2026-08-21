from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('EcommerceApp', '0001_initial')]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='Category',
            new_name='category',
        ),
    ]
