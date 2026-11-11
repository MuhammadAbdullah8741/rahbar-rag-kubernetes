from contextvars import ContextVar

tokens: ContextVar[tuple[int, int]] = ContextVar("generation_tokens", default=(0, 0))


def record_usage(input_count: int, output_count: int) -> None:
    previous = tokens.get()
    tokens.set((previous[0] + input_count, previous[1] + output_count))
