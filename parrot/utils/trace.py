import functools
import inspect
import types
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeGuard, TypeVar, cast

import discord
from discord.ext import commands

from parrot.config import logger
from parrot.utils import tag


TRACE_TYPES = (
	types.MethodType,
	types.FunctionType,
	types.BuiltinFunctionType,
	types.BuiltinMethodType,
	types.MethodDescriptorType,
	types.ClassMethodDescriptorType,
)


P = ParamSpec("P")
Ret = TypeVar("Ret")
AsyncFunction = Callable[P, Coroutine[Any, Any, Ret]]
SyncFunction = Callable[P, Ret]


def format_command_origin(ctx: commands.Context) -> str:
	result = ""
	if ctx.guild is not None:
		result += f"{ctx.guild.name} - "
	if isinstance(ctx.channel, discord.TextChannel):
		result += f"#{ctx.channel.name} - "
	result += tag(ctx.author)
	return result


def format_args(args: tuple) -> str:
	result = str(args)
	if len(args) == 1:
		# Remove annoying trailing comma
		result = result[:-2] + result[-1]
	return result


def format_kwargs(kwargs: dict) -> str:
	# TODO: make this prettier
	return str(kwargs)


def _do_trace(fn: Callable[P, Any], *args: P.args, **kwargs: P.kwargs) -> None:
	kwargs_str = format_kwargs(kwargs)
	if len(args) >= 2 and isinstance(args[0], commands.Cog):
		ctx = cast(commands.Context, args[1])
		command_origin = format_command_origin(ctx)
		args_str = format_args(args[2:])
		logger.debug(
			f"{command_origin}: "
			f"{args[0].__cog_name__}.{fn.__name__} {args_str} {kwargs_str}"
		)
	else:
		args_str = format_args(args[1:])
		logger.debug(f"{fn.__module__}.{fn.__name__} {args_str} {kwargs_str}")


def _trace_fn_async(fn: AsyncFunction) -> AsyncFunction:
	@functools.wraps(fn)
	async def async_decorated(*args: P.args, **kwargs: P.kwargs) -> object:
		_do_trace(fn, *args, **kwargs)
		return await fn(*args, **kwargs)

	return async_decorated


def _trace_fn_sync(fn: SyncFunction) -> SyncFunction:
	@functools.wraps(fn)
	def sync_decorated(*args: P.args, **kwargs: P.kwargs) -> object:
		_do_trace(fn, *args, **kwargs)
		return fn(*args, **kwargs)

	return sync_decorated


def _is_async(fn: AsyncFunction | SyncFunction) -> TypeGuard[AsyncFunction]:
	return inspect.iscoroutinefunction(fn)


def trace_fn[F: (AsyncFunction, SyncFunction)](fn: F) -> F:
	if _is_async(fn):
		return _trace_fn_async(fn)  # type: ignore dont know what you want from me
	else:
		return _trace_fn_sync(fn)  # type: ignore


def trace_class[Class](class_: Class) -> Class:
	for key in dir(class_):
		if key.startswith("_"):
			continue
		value = getattr(class_, key)
		if not isinstance(value, TRACE_TYPES):
			continue
		wrapped = trace_fn(value)
		setattr(class_, key, wrapped)
	return class_


def trace[T](thing: T) -> T:
	if isinstance(thing, TRACE_TYPES):
		return trace_fn(thing)
	return trace_class(thing)
