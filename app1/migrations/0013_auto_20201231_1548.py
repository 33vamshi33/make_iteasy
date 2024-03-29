# Generated by Django 3.0 on 2020-12-31 10:18

from django.db import migrations
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0012_broker_days'),
    ]

    operations = [
        migrations.AlterField(
            model_name='broker',
            name='days',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')], default=[0, 1, 2, 3, 4, 5], max_length=13),
        ),
    ]
