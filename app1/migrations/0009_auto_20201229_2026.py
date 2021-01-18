# Generated by Django 3.0 on 2020-12-29 14:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0008_feedback'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feedback',
            name='rating',
            field=models.IntegerField(choices=[(1, 'worst'), (2, 'bad'), (3, 'average'), (4, 'good'), (5, 'excellent')], default=4, max_length=1),
        ),
    ]
