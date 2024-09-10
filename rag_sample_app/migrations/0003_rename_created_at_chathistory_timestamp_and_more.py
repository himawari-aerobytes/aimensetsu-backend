# Generated by Django 5.0.6 on 2024-07-07 04:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rag_sample_app", "0002_chathistory"),
    ]

    operations = [
        migrations.RenameField(
            model_name="chathistory",
            old_name="created_at",
            new_name="timestamp",
        ),
        migrations.AddField(
            model_name="chathistory",
            name="thread_id",
            field=models.CharField(default="default_thread_id", max_length=100),
        ),
    ]
