# Generated by Django 2.2.28 on 2023-03-01 16:39

import django.contrib.postgres.fields.ranges
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import outpost.django.base.utils
import outpost.django.signage.validators
import recurrence.fields


class Migration(migrations.Migration):

    dependencies = [
        ('signage', '0004_auto_20230216_2210'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='page',
            options={'ordering': ('name',)},
        ),
        migrations.AlterField(
            model_name='pdfpage',
            name='pdf',
            field=models.FileField(help_text='PDF file to be used as a fullscreen page.', upload_to=outpost.django.base.utils.Uuid4Upload, validators=[outpost.django.signage.validators.PDFValidator(orientation=outpost.django.signage.validators.PDFOrientation(0), pages=range(1, 20))]),
        ),
        migrations.AlterField(
            model_name='playlistitem',
            name='enabled',
            field=models.BooleanField(default=True, help_text='Control visibility of item in playlist. Only enabled items are displayed.'),
        ),
        migrations.AlterField(
            model_name='playlistitem',
            name='page',
            field=models.ForeignKey(help_text='The page that should be used at this position of the playlist.', on_delete=django.db.models.deletion.CASCADE, to='signage.Page'),
        ),
        migrations.AlterField(
            model_name='schedule',
            name='default',
            field=models.ForeignKey(help_text='Select a playlist that should be used if no other playlist is scheduled at the moment.', on_delete=django.db.models.deletion.CASCADE, to='signage.Playlist'),
        ),
        migrations.AlterField(
            model_name='scheduleitem',
            name='playlist',
            field=models.ForeignKey(help_text='The playlist that should be displayed when this schedule becomes active.', on_delete=django.db.models.deletion.CASCADE, to='signage.Playlist'),
        ),
        migrations.AlterField(
            model_name='scheduleitem',
            name='range',
            field=django.contrib.postgres.fields.ranges.DateTimeRangeField(help_text='The absolute time range where this schedule can be considered active. Past items will automatically be cleaned up.'),
        ),
        migrations.AlterField(
            model_name='scheduleitem',
            name='recurrences',
            field=recurrence.fields.RecurrenceField(help_text='The dates on which this schedule will be active. Eligible dates will have the schedule start and stop at the selected time.'),
        ),
        migrations.AlterField(
            model_name='scheduleitem',
            name='start',
            field=models.TimeField(help_text='The time of the day when this schedule will start. Must be less than stop time.'),
        ),
        migrations.AlterField(
            model_name='scheduleitem',
            name='stop',
            field=models.TimeField(help_text='The time of the day when this schedule will stop. Must be greater than start time.'),
        ),
        migrations.AlterField(
            model_name='websitepage',
            name='url',
            field=models.URLField(help_text='URL of website to be used inside an IFRAME as a fullscreen page.', validators=[django.core.validators.URLValidator(schemes=('https',))]),
        ),
    ]
