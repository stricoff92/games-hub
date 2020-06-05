# Generated by Django 3.0.6 on 2020-05-25 14:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lobby', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField()),
                ('game_type', models.CharField(choices=[('texasholdem', "Texas Hold'Em"), ('connectquat', 'Connect-Quat')], max_length=24)),
                ('is_public', models.BooleanField(default=True)),
                ('is_full', models.BooleanField(default=False)),
                ('is_started', models.BooleanField(default=False)),
            ],
        ),
        migrations.AddField(
            model_name='player',
            name='slug',
            field=models.SlugField(default='asdasd'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='player',
            name='game',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='players', to='lobby.Game'),
            preserve_default=False,
        ),
    ]
