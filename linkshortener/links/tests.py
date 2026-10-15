import string

from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError

from .models import Link

CODE_LENGTH = 6
ALLOWED_CHARACTERS = set(string.ascii_letters + string.digits)


class LinkCodeTests(TestCase):
    """The code is generated in the model's save()."""

    def test_code_is_generated_when_missing(self):
        link = Link.objects.create(original_url="https://example.com")
        self.assertTrue(link.short_code)

    def test_code_has_right_length_and_characters(self):
        link = Link.objects.create(original_url="https://example.com")
        self.assertEqual(len(link.short_code), CODE_LENGTH)
        self.assertTrue(set(link.short_code) <= ALLOWED_CHARACTERS)

    def test_code_does_not_change_when_saved_again(self):
        link = Link.objects.create(original_url="https://example.com")
        first_code = link.short_code
        link.original_url = "https://example.org"
        link.save()
        link.refresh_from_db()
        self.assertEqual(link.short_code, first_code)

    def test_existing_code_is_kept(self):
        link = Link.objects.create(
            original_url="https://example.com", short_code="mycode"
        )
        self.assertEqual(link.short_code, "mycode")

    def test_codes_are_unique(self):
        codes = []
        for _ in range(50):
            link = Link.objects.create(original_url="https://example.com")
            codes.append(link.short_code)
        self.assertEqual(len(set(codes)), 50)


class RedirectTests(TestCase):
    """Visiting /<short_code>/ sends the visitor to the original URL."""

    @classmethod
    def setUpTestData(cls):
        cls.link = Link.objects.create(
            original_url="https://example.com/some/long/page"
        )

    def redirect_url(self, short_code=None):
        short_code = short_code or self.link.short_code
        return reverse("links:redirect", kwargs={"code": short_code})

    def test_valid_code_redirects_to_original_url(self):
        response = self.client.get(self.redirect_url())
        # assertRedirects expects a 302 by default, so a 301 would fail here.
        self.assertRedirects(
            response, self.link.original_url, fetch_redirect_response=False
        )

    def test_each_visit_increases_click_count(self):
        self.assertEqual(self.link.click_counter, 0)
        self.client.get(self.redirect_url())
        self.client.get(self.redirect_url())
        self.link.refresh_from_db()
        self.assertEqual(self.link.click_counter, 2)

    def test_visiting_does_not_change_the_code(self):
        first_code = self.link.short_code
        self.client.get(self.redirect_url())
        self.link.refresh_from_db()
        self.assertEqual(self.link.short_code, first_code)

    def test_unknown_code_gives_404(self):
        response = self.client.get(self.redirect_url("nope00"))
        self.assertEqual(response.status_code, 404)

    def test_unknown_code_does_not_change_any_clicks(self):
        self.client.get(self.redirect_url("nope00"))
        self.link.refresh_from_db()
        self.assertEqual(self.link.click_counter, 0)


class HomeAndDetailTests(TestCase):
    """Submitting a URL on the home page ends on the new link's detail page."""

    def test_home_page_loads(self):
        response = self.client.get(reverse("links:home"))
        self.assertEqual(response.status_code, 200)

    def test_submitting_a_url_creates_a_link_and_redirects_to_detail(self):
        response = self.client.post(
            reverse("links:home"),
            {"original_url": "https://example.com/some/long/page"},
        )
        link = Link.objects.get()
        self.assertTrue(link.short_code)
        self.assertRedirects(
            response,
            reverse("links:shortened_link", kwargs={"pk": link.pk}),
            fetch_redirect_response=False,
        )

    def test_detail_page_has_the_full_short_url(self):
        link = Link.objects.create(original_url="https://example.com")
        response = self.client.get(
            reverse("links:shortened_link", kwargs={"pk": link.pk})
        )
        path = reverse("links:redirect", kwargs={"code": link.short_code})
        # The test client's host is "testserver".
        self.assertEqual(
            response.context["short_url"], f"http://testserver{path}"
        )


class UrlOrderTests(TestCase):
    """The catch-all code route must not swallow other pages."""

    def test_admin_is_not_treated_as_a_code(self):
        response = self.client.get("/admin/")
        # A logged-out visitor is sent to the admin login (302), not a 404.
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])


"""====URL validator test===="""
HOME_URL = "/"
 
VALID_URLS = [
    "http://example.com",
    "https://example.com",
    "https://example.com/some/long/page?x=1&y=2#section",
]
 
INVALID_URLS = [
    "ftp://example.com/file.txt",  # URLField allows this by default
    "javascript:alert(1)",
    "data:text/html,<h1>hi</h1>",
    "file:///etc/passwd",
    "not a url",
    "",
]
 
 
def clean_link(url):
    """Run the model's validators. short_code is skipped because save() makes it."""
    link = Link(original_url=url)
    link.full_clean(exclude=["short_code"])
 
 
class LinkUrlModelTests(TestCase):
    """Validators run in full_clean() and in forms, but NOT in save()/create()."""
 
    def test_valid_urls_are_accepted(self):
        for url in VALID_URLS:
            with self.subTest(url=url):
                clean_link(url)  # raises ValidationError if the URL is rejected
 
    def test_invalid_urls_are_rejected(self):
        for url in INVALID_URLS:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError) as caught:
                    clean_link(url)
                self.assertIn("original_url", caught.exception.message_dict)
 
    def test_ftp_is_rejected(self):
        # The one that matters most: Django's default URLField accepts ftp://.
        with self.assertRaises(ValidationError):
            clean_link("ftp://example.com/file.txt")
 
 
class HomeFormUrlTests(TestCase):
    """The home page form should refuse bad URLs and save good ones."""
 
    def test_valid_url_is_saved_and_redirects_to_detail_page(self):
        url = "https://example.com/page"
        response = self.client.post(HOME_URL, {"original_url": url})
        link = Link.objects.get(original_url=url)
        self.assertRedirects(
            response, link.get_absolute_url(), fetch_redirect_response=False
        )
 
    def test_bad_urls_are_not_saved(self):
        for url in ["ftp://example.com/file.txt", "javascript:alert(1)"]:
            with self.subTest(url=url):
                response = self.client.post(HOME_URL, {"original_url": url})
                # The form is shown again with an error, not redirected.
                self.assertEqual(response.status_code, 200)
                self.assertIn("original_url", response.context["form"].errors)
                self.assertEqual(Link.objects.count(), 0)