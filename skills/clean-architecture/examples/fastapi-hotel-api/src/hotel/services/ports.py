"""Services layer: non-repository ports that use cases depend on."""

from collections.abc import Callable

IdFactory = Callable[[], str]
