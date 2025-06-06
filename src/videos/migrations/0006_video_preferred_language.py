# Generated by Django 5.2.1 on 2025-05-26 21:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("videos", "0005_transcript_content_word_count_video_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="video",
            name="preferred_language",
            field=models.CharField(
                choices=[
                    ("auto", "Auto-detect"),
                    ("en", "English"),
                    ("es", "Spanish"),
                    ("fr", "French"),
                    ("de", "German"),
                    ("pt", "Portuguese"),
                    ("ru", "Russian"),
                    ("it", "Italian"),
                    ("ja", "Japanese"),
                    ("ko", "Korean"),
                    ("zh", "Chinese"),
                    ("ar", "Arabic"),
                    ("hi", "Hindi"),
                    ("bn", "Bengali"),
                    ("ur", "Urdu"),
                    ("fa", "Persian/Farsi"),
                    ("th", "Thai"),
                    ("vi", "Vietnamese"),
                    ("tr", "Turkish"),
                    ("he", "Hebrew"),
                    ("am", "Amharic"),
                    ("sw", "Swahili"),
                    ("rw", "Kinyarwanda"),
                    ("ti", "Tigrinya"),
                    ("om", "Oromo"),
                    ("so", "Somali"),
                    ("ha", "Hausa"),
                    ("yo", "Yoruba"),
                    ("ig", "Igbo"),
                    ("ta", "Tamil"),
                    ("te", "Telugu"),
                    ("ml", "Malayalam"),
                    ("kn", "Kannada"),
                    ("gu", "Gujarati"),
                    ("mr", "Marathi"),
                    ("ne", "Nepali"),
                    ("si", "Sinhala"),
                    ("my", "Myanmar/Burmese"),
                    ("km", "Khmer"),
                    ("lo", "Lao"),
                    ("ka", "Georgian"),
                    ("hy", "Armenian"),
                    ("az", "Azerbaijani"),
                    ("kk", "Kazakh"),
                    ("ky", "Kyrgyz"),
                    ("uz", "Uzbek"),
                    ("tg", "Tajik"),
                    ("mn", "Mongolian"),
                ],
                default="auto",
                help_text="Select the expected language of the video to improve transcript accuracy",
                max_length=10,
                verbose_name="Preferred Language",
            ),
        ),
    ]
