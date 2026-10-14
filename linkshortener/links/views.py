from django.shortcuts import render
from django.views import generic
from django.urls import reverse
from django.shortcuts import redirect, get_object_or_404
from django.db.models import F

from .models import Link

class HomeView(generic.CreateView):
    model = Link
    fields = ['original_url']
    template_name = 'links/home.html'

class ShortenedLinkView(generic.DetailView):
    model = Link
    template_name = 'links/shortened_link.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        path = reverse('links:redirect', kwargs={'code': self.object.short_code})
        context["short_url"] = self.request.build_absolute_uri(path)
        return context
    
def redirectView(request, code):
    link = get_object_or_404(Link, short_code=code)
    Link.objects.filter(pk=link.pk).update(click_counter=F('click_counter') + 1)

    return redirect(link.original_url)
