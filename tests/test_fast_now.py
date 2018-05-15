import pendulum
import loguru


def test_fast_now():
    now_1 = loguru._fast_now.fast_now()
    assert isinstance(now_1, pendulum.DateTime)

    now_2 = loguru._fast_now.fast_now()
    assert now_2 >= now_1
