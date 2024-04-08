from __future__ import annotations

from poetry_plugin_export.command import (  # type: ignore[import-untyped]
    ExportCommand as BaseExportCommand,
)


class ExportCommand(BaseExportCommand):  # type: ignore[misc]
    def handle(self) -> int:
        if self.poetry.config.get("warnings.export"):
            self.line_error(
                "Warning: poetry-plugin-export will not be installed by default in a"
                " future version of Poetry.\n"
                "In order to avoid a breaking change and make your automation"
                " forward-compatible, please install poetry-plugin-export explicitly."
                " See https://python-poetry.org/docs/plugins/#using-plugins for details"
                " on how to install a plugin.\n"
                "To disable this warning run 'poetry config warnings.export false'.",
                style="warning",
            )
        return super().handle()  # type: ignore[no-any-return]
