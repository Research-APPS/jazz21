import json
import os

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.library.models import Progression


class LibrarySaveTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="testpass")
        self.client = Client()
        self.payload = {
            "saved_from": "widget",
            "title": "ii-V-I test",
            "key": "C",
            "mode": "ionian",
            "chords": ["Dm7", "G7", "Cmaj7"],
            "progression": {
                "nombre": "ii-V-I test",
                "tonalidad": "C",
                "modo": "ionian",
                "acordes": [
                    {"simbolo": "Dm7", "grado": "II", "funcion": "Subdominante"},
                    {"simbolo": "G7", "grado": "V", "funcion": "Dominante"},
                    {"simbolo": "Cmaj7", "grado": "I", "funcion": "Tónica"},
                ],
            },
            "widget_state": {"selected_key": "C", "selected_mode": "ionian"},
        }

    def test_save_rejects_anonymous(self):
        r = self.client.post(
            "/progressions/save/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["error"], "auth_required")

    def test_save_authenticated(self):
        self.client.login(username="tester", password="testpass")
        r = self.client.post(
            "/progressions/save/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertIn("uuid", data)
        prog = Progression.objects.get(uuid=data["uuid"])
        self.assertEqual(prog.title, "ii-V-I test")
        self.assertEqual(prog.chords_json, ["Dm7", "G7", "Cmaj7"])
        self.assertEqual(prog.source_json["title"], "ii-V-I test")
        self.assertEqual(prog.ontology_json["analysis_engine"], "manifest.py")
        self.assertEqual(prog.ontology_json["jazz21_version"], "0.2.0")

    def test_export_authenticated(self):
        self.client.login(username="tester", password="testpass")
        save = self.client.post(
            "/progressions/save/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        uuid = save.json()["uuid"]
        r = self.client.get(f"/progressions/{uuid}/export.json")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["uuid"], uuid)
        self.assertIn("source_json", data)

    def test_update_authenticated(self):
        self.client.login(username="tester", password="testpass")
        save = self.client.post(
            "/progressions/save/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        uuid = save.json()["uuid"]
        updated = dict(self.payload)
        updated["title"] = "ii-V-I actualizado"
        updated["progression"]["nombre"] = "ii-V-I actualizado"
        r = self.client.post(
            f"/progressions/{uuid}/save/",
            data=json.dumps(updated),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        prog = Progression.objects.get(uuid=uuid)
        self.assertEqual(prog.title, "ii-V-I actualizado")

    def test_detail_has_widget_bootstrap(self):
        self.client.login(username="tester", password="testpass")
        save = self.client.post(
            "/progressions/save/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        uuid = save.json()["uuid"]
        r = self.client.get(f"/progressions/{uuid}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'prog-widget-bootstrap', r.content)
        self.assertIn(b'data-library-uuid', r.content)


class SeedAdminTests(TestCase):
    def test_seed_admin_requires_password(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        os.environ.pop("JAZZ21_ADMIN_PASSWORD", None)
        with self.assertRaises(CommandError):
            call_command("seed_admin")

    def test_seed_admin_creates_user(self):
        from django.core.management import call_command

        os.environ["JAZZ21_ADMIN_PASSWORD"] = "testseed123"
        call_command("seed_admin")
        User = get_user_model()
        user = User.objects.get(username="ivansimo")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("testseed123"))
