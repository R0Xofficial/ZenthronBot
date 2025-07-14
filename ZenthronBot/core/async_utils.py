import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar, ParamSpec, Callable, Awaitable
from functools import partial

P = ParamSpec("P")
T = TypeVar("T")

_executor = ThreadPoolExecutor()

def aioify(func: Callable[P, T]) -> Callable[P, Awaitable[T]]:
    @partial(asyncio.coroutine)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        if asyncio.iscoroutinefunction(func):
            raise TypeError("Cannot aioify a coroutine function.")
        
        loop = asyncio.get_running_loop()
        
        return await loop.run_in_executor(
            _executor, partial(func, *args, **kwargs)
        )

    return wrapper
