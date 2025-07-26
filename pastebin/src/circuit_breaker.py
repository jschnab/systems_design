import enum
import functools
import random
from datetime import datetime, timedelta

from .log import get_logger

LOGGER = get_logger()


class CircuitBreakerException(Exception):
    def __init__(self, message, error):
        super().__init__(message)

        self.error = error


class CircuitBreakerBypass(Exception):
    def __init__(self, message):
        super().__init__(message)


class CircuitBreakerState(enum.Enum):
    CLOSED = 1
    OPEN = 2
    HALF_OPEN = 3


class AsyncCircuitBreaker:
    def __init__(
        self,
        monitored_exceptions=(Exception,),
        failure_monitor_timeout: int = 60,
        failure_rate_trigger: float = 0.5,
        min_calls_trigger: int = 10,
        open_timeout: int = 60,
        half_open_passthrough_rate: float = 0.5,
        recover_rate: float = 0.1,
        min_calls_recover: int = 10,
    ) -> None:
        self.monitored_exceptions = monitored_exceptions
        self.failure_monitor_timeout = failure_monitor_timeout
        self.failure_rate_trigger = failure_rate_trigger
        self.min_calls_trigger = min_calls_trigger

        self.open_timeout = open_timeout
        self.recover_rate = recover_rate
        self.min_calls_recover = min_calls_recover
        self.half_open_passthrough_rate = half_open_passthrough_rate

        self.trigger_timer_start = datetime.now()
        self.call_total = 0
        self.call_failures = 0
        self.last_failure_ts = None

        self.state = CircuitBreakerState.CLOSED

    def reset(self):
        self.reset_failure_tracking()
        self.state = CircuitBreakerState.CLOSED

    def reset_failure_tracking(self) -> None:
        self.trigger_timer_start = datetime.now()
        self.call_total = 0
        self.call_failures = 0

    def should_open_from_closed(self) -> bool:
        if self.call_total < self.min_calls_trigger:
            return False
        fail_rate = self.call_failures / self.call_total
        if fail_rate > self.failure_rate_trigger:
            return True
        return False

    def should_open_from_half_open(self) -> bool:
        if self.call_total < self.min_calls_trigger:
            return False
        fail_rate = self.call_failures / self.call_total
        if fail_rate > self.failure_rate_trigger:
            return True
        return False

    def should_close(self) -> bool:
        if self.call_total < self.min_calls_recover:
            return False
        fail_rate = self.call_failures / self.call_total
        if fail_rate < self.recover_rate:
            return True
        return False

    def log_msg_state_change(self, from_, to_):
        return f"{type(self).__name__} state changed from {from_} to {to_}"

    def __call__(self, func) -> None:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == CircuitBreakerState.OPEN:
                if datetime.now() > self.last_failure_ts + timedelta(
                    seconds=self.open_timeout
                ):
                    self.state = CircuitBreakerState.HALF_OPEN
                    LOGGER.info(self.log_msg_state_change("open", "half-open"))
                else:
                    raise CircuitBreakerBypass(
                        f"{type(self).__name__} state is open, bypassing "
                        f"{func.__module__}.{func.__name__}"
                    )

            if self.state == CircuitBreakerState.HALF_OPEN:
                if random.random() > self.half_open_passthrough_rate:
                    LOGGER.info(
                        f"{type(self).__name__} state is half-open, testing "
                        f"{func.__module__}.{func.__name__}"
                    )
                    self.call_total += 1
                    try:
                        result = await func(*args, **kwargs)
                        if self.should_close():
                            self.state = CircuitBreakerState.CLOSED
                            self.reset_failure_tracking()
                            LOGGER.info(
                                self.log_msg_state_change(
                                    "half-open", "closed"
                                )
                            )
                            return result
                    except self.monitored_exceptions as err:
                        LOGGER.error(
                            f"{type(self).__name__} in half-open state caught "
                            f"{err.__class__.__name__} when calling "
                            f"{func.__module__}.{func.__name__}: {err}"
                        )
                        self.call_failures += 1
                        self.last_failure_ts = datetime.now()
                        if self.should_open_from_half_open():
                            self.reset_failure_tracking()
                            self.state = CircuitBreakerState.OPEN
                            LOGGER.info(
                                self.log_msg_state_change("half-open", "open")
                            )
                        raise CircuitBreakerException(
                            message=(
                                f"{type(err).__name__} raised by "
                                f"{func.__module__}.{func.__name__}"
                            ),
                            error=err,
                        )
                else:
                    raise CircuitBreakerBypass(
                        f"{type(self).__name__} state is half-open, bypassing "
                        f"{func.__module__}.{func.__name__}"
                    )

            if self.state == CircuitBreakerState.CLOSED:
                LOGGER.info(
                    f"{type(self).__name__} state is closed, calling "
                    f"{func.__module__}.{func.__name__}"
                )
                if datetime.now() > self.trigger_timer_start + timedelta(
                    seconds=self.failure_monitor_timeout
                ):
                    self.reset_failure_tracking()

                self.call_total += 1

                try:
                    return await func(*args, **kwargs)
                except self.monitored_exceptions as err:
                    LOGGER.error(
                        f"{type(self).__name__} in closed state caught "
                        f"{type(err).__name__} when calling "
                        f"{func.__module__}.{func.__name__}: {err}"
                    )
                    self.call_failures += 1
                    self.last_failure_ts = datetime.now()
                    if self.should_open_from_closed():
                        self.state = CircuitBreakerState.OPEN
                        self.reset_failure_tracking()
                        LOGGER.info(
                            self.log_msg_state_change("closed", "open")
                        )
                    raise CircuitBreakerException(
                        message=(
                            f"{type(err).__name__} raised by "
                            f"{func.__module__}.{func.__name__}"
                        ),
                        error=err,
                    )

        return wrapper
