# Generated by Django 5.0.6 on 2024-07-21 09:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rag_sample_app', '0006_thread_creator'),
    ]

    operations = [
        migrations.AddField(
            model_name='thread',
            name='first_message',
            field=models.TextField(blank=True, null=True),
        ),
    ]
