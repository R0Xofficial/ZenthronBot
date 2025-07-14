import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar, ParamSpec, Callable, Awaitable
from functools import wraps

P = ParamSpec("P")
T = TypeVar("T")

_executor = ThreadPoolExecutor()

def aioify(func: Callable[P, T]) -> Callable[P, Awaitable[T]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        if asyncio.iscoroutinefunction(func):
            raise TypeError("Cannot aioify a coroutine function.")
        
        loop = asyncio.get_running_loop()
        
        return await loop.run_in_executor(
            _executor, 
            lambda: func(*args, **kwargs)
        )

    return wrapper
