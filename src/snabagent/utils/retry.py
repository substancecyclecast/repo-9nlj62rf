from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential


def default_retrying(max_attempts: int = 3) -> AsyncRetrying:
    return AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(min=1, max=10),
        reraise=True,
    )
