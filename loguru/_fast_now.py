import pendulum

# TODO: Update with Pendulum v2
# def get_fast_now_function():
#     try:
#         from ._extensions.fast_now import init, now
#         raise ImportError
#     except ImportError:
#         fast_now = pendulum.now
#     else:
#         local_timezone = pendulum.tz.local_timezone()

#         tzinfos = local_timezone.tzinfos
#         transitions = local_timezone.transitions
#         timestamps = [tr.unix_time for tr in transitions]
#         indexes = [tr.pre_tzinfo_index for tr in transitions]
#         default_index = local_timezone._default_tzinfo_index

#         # TODO: init(DateTime) and then just use now() when Pendulum v2.0.0 will be published
#         from pendulum import Pendulum
#         from datetime import datetime
#         init(datetime, tzinfos, timestamps, indexes, default_index)

#         def fast_now():
#             dt = now()

#             return Pendulum(dt.year, dt.month, dt.day,
#                             dt.hour, dt.minute, dt.second, dt.microsecond,
#                             dt.tzinfo, dt.fold)

#     return fast_now

def get_fast_now_function():
    return pendulum.now

fast_now = get_fast_now_function()
