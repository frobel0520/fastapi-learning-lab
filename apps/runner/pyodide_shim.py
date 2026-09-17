"""Thread-free execution helpers for running the harness inside Pyodide.

Pyodide has no threads. Starlette's TestClient drives the ASGI app through an
anyio blocking portal (a worker thread), sync endpoints run in anyio's thread
pool, and a2wsgi runs WSGI apps in a ThreadPoolExecutor. This module replaces
those three entry points with inline equivalents that run on the single
Pyodide event loop and block with JSPI's ``run_sync``.

It is only imported by the browser runner; the container runner never loads it.
"""
import asyncio
import concurrent.futures
import contextlib
import inspect

import anyio.from_thread
import anyio.to_thread
from pyodide.ffi import run_sync


async def _run_inline(func, *args, abandon_on_cancel=False, cancellable=None, limiter=None):
    return func(*args)


async def _await(awaitable):
    return await awaitable


async def _call(func, *args):
    result = func(*args)
    if inspect.isawaitable(result):
        result = await result
    return result


class _TaskFuture(concurrent.futures.Future):
    """A concurrent future whose ``result()`` waits on the event loop instead of a lock."""

    task: asyncio.Task | None = None

    def result(self, timeout=None):
        if not self.done() and self.task is not None:
            run_sync(asyncio.wait({self.task}))
        return super().result(timeout=0)


class _TaskStatus:
    def __init__(self, started: asyncio.Future) -> None:
        self._started = started

    def started(self, value=None) -> None:
        if not self._started.done():
            self._started.set_result(value)


class InlinePortal:
    """The subset of ``anyio.abc.BlockingPortal`` used by Starlette's TestClient."""

    def __init__(self) -> None:
        self.tasks: list[asyncio.Task] = []

    def call(self, func, *args):
        return run_sync(_call(func, *args))

    def _spawn(self, coroutine) -> _TaskFuture:
        future = _TaskFuture()

        async def runner():
            try:
                result = await coroutine
            except BaseException as error:
                future.set_exception(error)
            else:
                future.set_result(result)

        future.task = asyncio.get_event_loop().create_task(runner())
        self.tasks.append(future.task)
        return future

    def start_task_soon(self, func, *args, name=None):
        return self._spawn(_call(func, *args))

    def start_task(self, func, *args, name=None):
        started = asyncio.get_event_loop().create_future()

        async def with_status():
            try:
                return await func(*args, task_status=_TaskStatus(started))
            except BaseException as error:
                if not started.done():
                    started.set_exception(error)
                raise

        future = self._spawn(with_status())
        return future, run_sync(_await(started))


@contextlib.contextmanager
def start_blocking_portal(backend="asyncio", backend_options=None, **_):
    portal = InlinePortal()
    try:
        yield portal
    finally:
        for task in portal.tasks:
            if not task.done():
                task.cancel()


class InlineExecutor(concurrent.futures.Executor):
    def __init__(self, *args, **kwargs) -> None:
        pass

    def submit(self, fn, /, *args, **kwargs):
        future = concurrent.futures.Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as error:
            future.set_exception(error)
        return future

    def shutdown(self, wait=True, *, cancel_futures=False) -> None:
        pass


class _CoroutineResult:
    def __init__(self, coroutine) -> None:
        self._coroutine = coroutine

    def result(self, timeout=None):
        return run_sync(self._coroutine)


class _A2wsgiAsyncio:
    """``asyncio`` as seen by a2wsgi, with thread hand-offs turned into inline waits."""

    def __getattr__(self, name):
        return getattr(asyncio, name)

    @staticmethod
    def run_coroutine_threadsafe(coroutine, loop):
        return _CoroutineResult(coroutine)


def install() -> None:
    anyio.to_thread.run_sync = _run_inline
    anyio.from_thread.start_blocking_portal = start_blocking_portal
    try:
        import a2wsgi.wsgi
    except ImportError:
        return
    a2wsgi.wsgi.ThreadPoolExecutor = InlineExecutor
    a2wsgi.wsgi.asyncio = _A2wsgiAsyncio()


def reset_between_runs() -> None:
    """Clear process-wide state that learner code registers at import time."""
    try:
        from sqlmodel import SQLModel
    except ImportError:
        return
    SQLModel.metadata.clear()
