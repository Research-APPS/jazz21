from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Crea o actualiza el superusuario ivansimo desde JAZZ21_ADMIN_PASSWORD."

    def handle(self, *args, **options):
        import os

        password = os.environ.get("JAZZ21_ADMIN_PASSWORD")
        if not password:
            raise CommandError(
                "Define JAZZ21_ADMIN_PASSWORD en el entorno antes de ejecutar seed_admin."
            )

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username="ivansimo",
            defaults={"is_staff": True, "is_superuser": True},
        )
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        verb = "Creado" if created else "Actualizado"
        self.stdout.write(self.style.SUCCESS(f"{verb} superusuario ivansimo"))
