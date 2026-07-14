from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class TaskDayDataMigrationTest(TransactionTestCase):
    migrate_from = [("task", "0005_studysession_sessionpause_subject_topic_and_more")]
    migrate_to = [("task", "0006_taskday_data_migration")]
    migrate_latest = [("task", "0008_studyinsight")]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps

        TaskDay = old_apps.get_model("task", "TaskDay")
        User = old_apps.get_model("auth", "User")

        self.user = User.objects.create(username="testuser")
        TaskDay.objects.create(user=self.user, date=date(2023, 10, 1))
        TaskDay.objects.create(user=self.user, date=date(2023, 10, 2))

    def tearDown(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_latest)
        super().tearDown()

    def test_migration_converts_taskday_to_studysession(self):
        self.executor.loader.build_graph()
        self.executor.migrate(self.migrate_to)
        new_apps = self.executor.loader.project_state(self.migrate_to).apps

        StudySession = new_apps.get_model("task", "StudySession")
        Subject = new_apps.get_model("task", "Subject")
        Topic = new_apps.get_model("task", "Topic")

        self.assertEqual(StudySession.objects.count(), 2)

        session = StudySession.objects.first()
        self.assertEqual(session.user_id, self.user.id)
        self.assertEqual(session.objective_text, "Migração Legada")
        self.assertEqual(session.status, "COMPLETED")
        self.assertEqual(session.mode, "FREE")
        self.assertEqual(session.objective_achieved, "PENDING")

        subject = Subject.objects.get(name="Migração Legada", user_id=self.user.id)
        topic = Topic.objects.get(name="Geral", subject_id=subject.id)
        self.assertEqual(session.topic_id, topic.id)

        start_date = session.start_time.date()
        self.assertIn(start_date, [date(2023, 10, 1), date(2023, 10, 2)])

    def test_migration_rollback_removes_generated_study_data(self):
        self.executor.loader.build_graph()
        self.executor.migrate(self.migrate_to)
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        rolled_back_apps = self.executor.loader.project_state(self.migrate_from).apps

        StudySession = rolled_back_apps.get_model("task", "StudySession")
        Subject = rolled_back_apps.get_model("task", "Subject")
        Topic = rolled_back_apps.get_model("task", "Topic")
        TaskDay = rolled_back_apps.get_model("task", "TaskDay")

        self.assertEqual(TaskDay.objects.count(), 2)
        self.assertEqual(StudySession.objects.count(), 0)
        self.assertEqual(Topic.objects.filter(name="Geral").count(), 0)
        self.assertEqual(Subject.objects.filter(name="MigraÃ§Ã£o Legada").count(), 0)
