"""File system watcher for automatic rebuilds."""

import time
from pathlib import Path
from threading import Timer
from typing import Callable

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from pinecone.bundler import BundleResult, bundle, write_bundle
from pinecone.config import PineconeConfig


class PineFileHandler(FileSystemEventHandler):
    """Handle .pine file changes with debouncing."""

    def __init__(
        self,
        config: PineconeConfig,
        on_success: Callable[[BundleResult], None],
        on_error: Callable[[Exception], None],
        debounce_seconds: float = 0.1,
    ) -> None:
        self.config = config
        self.on_success = on_success
        self.on_error = on_error
        self.debounce_seconds = debounce_seconds
        self._timer: Timer | None = None
        super().__init__()

    def _should_handle(self, event: FileSystemEvent) -> bool:
        """Check if this event should trigger a rebuild."""
        if event.is_directory:
            return False

        path = Path(event.src_path)

        # Only handle .pine files
        if path.suffix != ".pine":
            return False

        # Ignore output file
        if path.resolve() == self.config.output.resolve():
            return False

        return True

    def _do_rebuild(self) -> None:
        """Execute the rebuild."""
        try:
            result = bundle(self.config)
            write_bundle(result)
            self.on_success(result)
        except Exception as e:
            self.on_error(e)

    def _schedule_rebuild(self) -> None:
        """Schedule a rebuild with debouncing."""
        # Cancel any pending rebuild
        if self._timer is not None:
            self._timer.cancel()

        # Schedule new rebuild
        self._timer = Timer(self.debounce_seconds, self._do_rebuild)
        self._timer.start()

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification."""
        if self._should_handle(event):
            self._schedule_rebuild()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation."""
        if self._should_handle(event):
            self._schedule_rebuild()

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion."""
        if self._should_handle(event):
            self._schedule_rebuild()


def watch_and_rebuild(
    config: PineconeConfig,
    on_success: Callable[[BundleResult], None],
    on_error: Callable[[Exception], None],
    debounce_seconds: float = 0.1,
) -> None:
    """Watch project files and trigger rebuilds on changes.

    This function blocks until interrupted (Ctrl+C).

    Args:
        config: Project configuration.
        on_success: Callback for successful builds.
        on_error: Callback for build errors.
        debounce_seconds: Debounce delay for rapid saves.
    """
    handler = PineFileHandler(config, on_success, on_error, debounce_seconds)

    observer = Observer()
    observer.schedule(handler, str(config.root_dir), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
