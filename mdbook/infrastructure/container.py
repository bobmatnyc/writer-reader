"""Dependency injection container for service composition.

Provides a simple IoC container for wiring up dependencies following
the composition root pattern.
"""

from typing import Callable, TypeVar, Dict, Any

from ..repositories import (
    IFileRepository,
    IConfigRepository,
    FileRepository,
    ConfigRepository,
)
from ..services import (
    IStructureService,
    IReaderService,
    IWriterService,
    IBookService,
    StructureService,
    ReaderService,
    WriterService,
    BookService,
    ContentService,
    RenderService,
    TocService,
    IndexService,
)

T = TypeVar("T")


class ServiceContainer:
    """Simple dependency injection container.

    Supports singleton and transient lifetime management for registered
    services. Services are resolved lazily on first access.
    """

    def __init__(self) -> None:
        """Initialize an empty service container."""
        self._factories: Dict[type, tuple[Callable[[], Any], bool]] = {}
        self._singletons: Dict[type, Any] = {}

    def register(
        self,
        service_type: type,
        factory: Callable[[], T],
        singleton: bool = True,
    ) -> None:
        """Register a service factory.

        Args:
            service_type: The interface/protocol type to register.
            factory: A callable that creates the service instance.
            singleton: If True, cache the instance for reuse.
        """
        self._factories[service_type] = (factory, singleton)

    def resolve(self, service_type: type[T]) -> T:
        """Resolve a service instance by its type.

        Args:
            service_type: The interface/protocol type to resolve.

        Returns:
            The service instance.

        Raises:
            KeyError: If the service type is not registered.
        """
        if service_type in self._singletons:
            return self._singletons[service_type]

        factory, singleton = self._factories[service_type]
        instance = factory()

        if singleton:
            self._singletons[service_type] = instance
        return instance


def configure_services() -> ServiceContainer:
    """Composition root - wire up all dependencies.

    Creates and configures a ServiceContainer with all application
    services properly wired together.

    Returns:
        A fully configured ServiceContainer ready for use.
    """
    container = ServiceContainer()

    # Register repositories
    container.register(IFileRepository, lambda: FileRepository())
    container.register(IConfigRepository, lambda: ConfigRepository())

    # Register structure service
    container.register(
        IStructureService,
        lambda: StructureService(
            container.resolve(IFileRepository),
            container.resolve(IConfigRepository),
        ),
    )

    # Register reader service
    container.register(
        IReaderService,
        lambda: ReaderService(
            container.resolve(IFileRepository),
            container.resolve(IConfigRepository),
            container.resolve(IStructureService),
        ),
    )

    # Register writer service
    container.register(
        IWriterService,
        lambda: WriterService(
            container.resolve(IFileRepository),
            container.resolve(IConfigRepository),
            container.resolve(IStructureService),
        ),
    )

    # Register book service facade
    container.register(
        IBookService,
        lambda: BookService(
            container.resolve(IReaderService),
            container.resolve(IWriterService),
        ),
    )

    # Register content service
    container.register(
        ContentService,
        lambda: ContentService(
            container.resolve(IFileRepository),
        ),
    )

    # Register render service
    container.register(
        RenderService,
        lambda: RenderService(
            container.resolve(IFileRepository),
            container.resolve(IReaderService),
        ),
    )

    # Register TOC service
    container.register(
        TocService,
        lambda: TocService(
            container.resolve(IReaderService),
        ),
    )

    # Register index service
    container.register(
        IndexService,
        lambda: IndexService(
            container.resolve(IReaderService),
        ),
    )

    return container
