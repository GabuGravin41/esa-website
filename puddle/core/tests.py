from django.test import TestCase
from .models import Event, BlogPost
from django.urls import reverse

# Create your tests here.

class EventModelTest(TestCase):
    def setUp(self):
        Event.objects.create(name="Test Event", is_active=True)

    def test_event_creation(self):
        event = Event.objects.get(name="Test Event")
        self.assertTrue(event.is_active)

class HomeViewTest(TestCase):
    def test_home_view_status_code(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_home_view_template(self):
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'core/home.html')
