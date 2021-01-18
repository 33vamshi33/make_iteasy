# Generated by Django 3.0 on 2021-01-02 10:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0016_connection_is_read'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='connection',
            name='is_read',
        ),
        migrations.RemoveField(
            model_name='message',
            name='is_read',
        ),
        migrations.AddField(
            model_name='connection',
            name='is_brokerread',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='connection',
            name='is_customerread',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='message',
            name='is_brokerread',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='message',
            name='is_customerread',
            field=models.BooleanField(default=False),
        ),
    ]
