# Generated by Django 5.0.6 on 2025-02-13 09:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0002_remove_promodetail_unique_promo_price_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='package',
            name='promo',
            field=models.BooleanField(default=False),
        ),
    ]
