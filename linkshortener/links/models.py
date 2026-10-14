from django.db import models
from django.urls import reverse

import secrets
import string


alpha_num = string.ascii_letters + string.digits

class Link(models.Model):
    original_url = models.URLField(max_length=2000)
    short_code = models.CharField(max_length=6, unique=True, blank=True)
    click_counter = models.IntegerField(default=0)
    date_created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.short_code:

            while True:
                code = ''.join(secrets.choice(alpha_num) for i in range(6))
                if Link.objects.filter(short_code=code).exists():
                    continue
                else:
                    self.short_code = code
                    break

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("links:shortened_link", kwargs={"pk": self.pk})
    
