from django.contrib.auth.models import User
from django.test import TestCase
from faker import Faker

from task.forms import TopicForm
from task.models import Subject, Topic

fake = Faker()


class TopicFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=fake.user_name(), email=fake.email(), password=fake.password()
        )
        self.subject = Subject.objects.create(user=self.user, name=fake.word())

    def test_topic_form_valid_with_default_priority(self):
        form = TopicForm(
            data={"subject": self.subject.id, "name": "Docker", "priority": "MEDIUM"},
            user=self.user,
        )
        self.assertTrue(form.is_valid())
        topic = form.save()
        self.assertEqual(topic.priority, Topic.Priority.MEDIUM)

    def test_topic_form_valid_with_high_priority(self):
        form = TopicForm(
            data={"subject": self.subject.id, "name": "Kubernetes", "priority": "HIGH"},
            user=self.user,
        )
        self.assertTrue(form.is_valid())
        topic = form.save()
        self.assertEqual(topic.priority, Topic.Priority.HIGH)

    def test_topic_form_invalid_priority(self):
        form = TopicForm(
            data={"subject": self.subject.id, "name": "Invalid", "priority": "CRITICAL"},
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("priority", form.errors)
