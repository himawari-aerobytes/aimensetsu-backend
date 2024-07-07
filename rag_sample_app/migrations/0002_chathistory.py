# Generated by Django 5.0.6 on 2024-07-02 08:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rag_sample_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_input', models.TextField()),
                ('ai_response', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
