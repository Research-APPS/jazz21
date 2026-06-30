from django.contrib import admin

from apps.library.models import (
    Bookmark,
    Comment,
    Progression,
    ProgressionVersion,
    Project,
    Study,
    Tag,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "color", "user")
    list_filter = ("kind",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "updated_at")
    search_fields = ("title",)


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "user", "updated_at")


@admin.register(Progression)
class ProgressionAdmin(admin.ModelAdmin):
    list_display = ("title", "uuid", "key", "mode", "user", "updated_at")
    search_fields = ("title", "uuid")
    readonly_fields = ("uuid",)


@admin.register(ProgressionVersion)
class ProgressionVersionAdmin(admin.ModelAdmin):
    list_display = ("progression", "version_number", "parent_version", "created_at")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("progression", "user", "created_at")


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("progression", "kind", "user", "created_at")
