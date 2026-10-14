from django.db import models

class Link(models.Model):
    original_url = models.URLField(max_length=2000)
    short_code = models.CharField(max_length=6, unique=True, blank=True)
    click_counter = models.IntegerField(default=0)
    date_created = models.DateTimeField(auto_now_add=True)
