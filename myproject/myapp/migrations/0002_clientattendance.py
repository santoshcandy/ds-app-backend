# Generated by Django 5.1.7 on 2025-03-25 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_id', models.IntegerField(unique=True)),
                ('date', models.DateField(auto_now_add=True)),
                ('is_present', models.BooleanField(default=False)),
                ('check_in_time', models.TimeField(blank=True, null=True)),
            ],
        ),
    ]
