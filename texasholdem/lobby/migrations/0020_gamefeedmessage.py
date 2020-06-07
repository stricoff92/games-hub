# Generated by Django 3.0.6 on 2020-06-07 18:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lobby', '0019_game_max_seconds_per_turn'),
    ]

    operations = [
        migrations.CreateModel(
            name='GameFeedMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('message', models.CharField(max_length=300)),
                ('message_type', models.CharField(choices=[('move', 'Player Moved'), ('quit', 'Player Quit'), ('status', 'Game Status')], max_length=10)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lobby.Game')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
