# Generated by Django 3.2 on 2021-04-24 07:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('uth_groups_app', '0015_course_datetime'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='participants',
            field=models.ManyToManyField(blank=True, null=True, to='uth_groups_app.Student'),
        ),
    ]