from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("task", "0006_taskday_data_migration"),
    ]

    operations = [
        migrations.AddField(
            model_name="studysession",
            name="learning_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="studysession",
            name="next_step",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="studysession",
            name="objective_result",
            field=models.TextField(blank=True),
        ),
    ]
