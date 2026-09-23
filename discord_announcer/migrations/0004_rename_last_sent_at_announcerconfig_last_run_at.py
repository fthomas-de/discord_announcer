import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('discord_announcer', '0003_announcerconfig_delete_lastrun'),
    ]

    operations = [
        migrations.RenameField(
            model_name='announcerconfig',
            old_name='last_sent_at',
            new_name='last_run_at',
        ),
        migrations.AlterField(
            model_name='announcerconfig',
            name='last_run_at',
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='Last run at'),
        ),
        migrations.AlterField(
            model_name='announcerconfig',
            name='time_delta',
            field=models.PositiveIntegerField(default=12, help_text='Posts every this many hours, covering the sales since the previous post. At least one hour.', validators=[django.core.validators.MinValueValidator(1)], verbose_name='Interval (hours)'),
        ),
    ]
