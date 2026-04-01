from django.apps import AppConfig


class TracesConfig(AppConfig):
    name = "traces"

    def ready(self):
        import traces.signals  # noqa: F401
