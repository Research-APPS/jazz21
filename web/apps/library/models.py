from django.db import models
from django.conf import settings
import uuid


class Tag(models.Model):
    KIND_CHOICES = [
        ("tema", "Tema"),
        ("color", "Color"),
        ("emocion", "Emoción"),
        ("modo", "Modo"),
        ("genero", "Género"),
        ("referencia", "Referencia"),
    ]

    name = models.CharField(max_length=80)
    color = models.CharField(max_length=7, default="#8b9cb3")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="tema")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tags",
    )

    class Meta:
        unique_together = [("user", "name", "kind")]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Project(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title


class Study(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="studies",
    )
    project = models.ForeignKey(
        Project,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="studies",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="studies")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name_plural = "studies"

    def __str__(self) -> str:
        return self.title


class Progression(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="progressions",
    )
    project = models.ForeignKey(
        Project,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="progressions",
    )
    study = models.ForeignKey(
        Study,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="progressions",
    )
    head_version = models.ForeignKey(
        "ProgressionVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    source_json = models.JSONField(default=dict)
    title = models.CharField(max_length=200)
    key = models.CharField(max_length=10)
    mode = models.CharField(max_length=20, default="ionian")
    chords_json = models.JSONField(default=list)
    analysis_json = models.JSONField(default=list)
    ontology_json = models.JSONField(default=dict)
    widget_state_json = models.JSONField(default=dict)
    tags = models.ManyToManyField(Tag, blank=True, related_name="progressions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if self.study_id and self.study and self.study.user_id != self.user_id:
            raise ValidationError({"study": "El estudio debe pertenecer al mismo usuario."})
        if self.project_id and self.project and self.project.user_id != self.user_id:
            raise ValidationError({"project": "El proyecto debe pertenecer al mismo usuario."})
        if self.study_id and self.study and self.study.project_id:
            if self.project_id and self.project_id != self.study.project_id:
                raise ValidationError({"project": "Debe coincidir con el proyecto del estudio."})
            if not self.project_id:
                self.project = self.study.project


class ProgressionVersion(models.Model):
    progression = models.ForeignKey(
        Progression,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    parent_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    chords_json = models.JSONField(default=list)
    analysis_json = models.JSONField(default=list)
    ontology_json = models.JSONField(default=dict)
    widget_state_json = models.JSONField(default=dict)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["version_number"]
        unique_together = [("progression", "version_number")]

    def __str__(self) -> str:
        return f"{self.progression.title} v{self.version_number}"


class Comment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="progression_comments",
    )
    progression = models.ForeignKey(
        Progression,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment on {self.progression_id}"


class Bookmark(models.Model):
    KIND_CHOICES = [
        ("favorita", "Favorita"),
        ("pendiente", "Pendiente"),
        ("para_estudiar", "Para estudiar"),
        ("para_proyecto", "Para proyecto"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    progression = models.ForeignKey(
        Progression,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="favorita")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "progression", "kind")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kind} → {self.progression.title}"
