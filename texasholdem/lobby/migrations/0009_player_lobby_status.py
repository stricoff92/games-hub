# Generated by Django 3.0.6 on 2020-05-31 01:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lobby', '0008_auto_20200530_1931'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='lobby_status',
            field=models.CharField(choices=[('joined', 'Joined'), ('ready', 'Ready')], default='joined', max_length=12),
        ),
    ]
