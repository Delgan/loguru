#include <Python.h>
#include <datetime.h>
//#include <structmember.h>
#include <time.h>

static PyTypeObject *fast_now_class = NULL;
static PyObject *fast_now_tzinfos = NULL;
static PyObject *fast_now_timestamps = NULL;
static PyObject *fast_now_indexes = NULL;

static PyObject *fast_now_tzinfo = NULL;
static long long fast_now_post_transition_secs;
static long long fast_now_pre_transition_secs;
static Py_ssize_t fast_now_transition_index;

static PyObject *
fast_now_init(PyObject *self, PyObject *args)
{
    PyObject *class;
    PyObject *tzinfos;
    PyObject *timestamps;
    PyObject *indexes;
    Py_ssize_t default_index;

    if (!PyArg_ParseTuple(args, "OOOOn", &class, &tzinfos, &timestamps, &indexes, &default_index)) {
        return NULL;
    }

    if (!PyType_Check(class)) {
        PyErr_SetString(PyExc_TypeError, "1st argument (class) is not a valid type");
        return NULL;
    }

    tzinfos = PySequence_Fast(tzinfos, "2nd argument (tzinfos) is not a valid sequence");
    if (tzinfos == NULL) {
        return NULL;
    }

    timestamps = PySequence_Fast(timestamps, "3rd argument (timestamps) is not a valid sequence");
    if (timestamps == NULL) {
        return NULL;
    }

    indexes = PySequence_Fast(indexes, "4th argument (indexes) is not a valid sequence");
    if (indexes == NULL) {
        return NULL;
    }

    if (PySequence_Fast_GET_SIZE(timestamps) != PySequence_Fast_GET_SIZE(indexes)) {
        PyErr_SetString(PyExc_TypeError, "Timestamps and Indexes does not have the same size");
        return NULL;
    }

    Py_XDECREF(fast_now_class);
    Py_XDECREF(fast_now_tzinfos);
    Py_XDECREF(fast_now_timestamps);
    Py_XDECREF(fast_now_indexes);
    Py_XDECREF(fast_now_tzinfo);

    fast_now_class = (PyTypeObject *)class;
    fast_now_tzinfos = tzinfos;
    fast_now_timestamps = timestamps;
    fast_now_indexes = indexes;
    fast_now_tzinfo = PySequence_Fast_GET_ITEM(tzinfos, default_index);
    fast_now_pre_transition_secs = PY_LLONG_MIN;
    fast_now_post_transition_secs = PY_LLONG_MIN;
    fast_now_transition_index = -1;

    Py_INCREF(fast_now_class);
    Py_INCREF(fast_now_tzinfos);
    Py_INCREF(fast_now_timestamps);
    Py_INCREF(fast_now_indexes);
    Py_INCREF(fast_now_tzinfo);

    Py_RETURN_NONE;
}

static PyObject *
fast_now_now(PyObject *self, PyObject *args)
{
    /*
    Reimplementation of an internal helper:
    https://github.com/python/cpython/blob/9b99747386b690007027c3be2a5d7cfe3d3634f5/Modules/_datetimemodule.c#L4625-L4641
    */

    // 0. Accessors
    #define SET_YEAR(o, v)          (((o)->data[0] = ((v) & 0xff00) >> 8), \
                     ((o)->data[1] = ((v) & 0x00ff)))
    #define SET_MONTH(o, v)         (PyDateTime_GET_MONTH(o) = (v))
    #define SET_DAY(o, v)           (PyDateTime_GET_DAY(o) = (v))
    #define DATE_SET_HOUR(o, v)     (PyDateTime_DATE_GET_HOUR(o) = (v))
    #define DATE_SET_MINUTE(o, v)   (PyDateTime_DATE_GET_MINUTE(o) = (v))
    #define DATE_SET_SECOND(o, v)   (PyDateTime_DATE_GET_SECOND(o) = (v))
    #define DATE_SET_MICROSECOND(o, v)      \
        (((o)->data[7] = ((v) & 0xff0000) >> 16), \
         ((o)->data[8] = ((v) & 0x00ff00) >> 8), \
         ((o)->data[9] = ((v) & 0x0000ff)))
    #define DATE_SET_FOLD(o, v) (PyDateTime_DATE_GET_FOLD(o) = (v))

    // 1. datetime_best_possible()
    _PyTime_t ts = _PyTime_GetSystemClock();
    time_t secs;
    int usecond;

    if (_PyTime_AsTimevalTime_t(ts, &secs, &usecond, _PyTime_ROUND_FLOOR) < 0)
        return NULL;

    // X. Update cached tzinfo if needed
    if (secs >= fast_now_post_transition_secs || secs < fast_now_pre_transition_secs) {
        Py_ssize_t idx;
        long long pre_tr_secs;
        Py_ssize_t size = PySequence_Fast_GET_SIZE(fast_now_timestamps);

        if (secs >= fast_now_post_transition_secs) {
            idx = fast_now_transition_index;
            pre_tr_secs = fast_now_post_transition_secs;
        } else {
            idx = -1;
            pre_tr_secs = PY_LLONG_MIN;
        }

        while (idx < size) {
            idx++;
            if (idx == size) {
                fast_now_pre_transition_secs = fast_now_post_transition_secs;
                fast_now_post_transition_secs = PY_LLONG_MAX;
                fast_now_transition_index = idx;
                break;
            }

            long long post_tr_secs = PyLong_AsLongLong(PySequence_Fast_GET_ITEM(fast_now_timestamps, idx));

            if (post_tr_secs > secs) {
                fast_now_pre_transition_secs = pre_tr_secs;
                fast_now_post_transition_secs = post_tr_secs;
                fast_now_transition_index = idx;
                Py_ssize_t tr_index = PyLong_AsLongLong(PySequence_Fast_GET_ITEM(fast_now_indexes, idx));
                Py_DECREF(fast_now_tzinfo);
                fast_now_tzinfo = PySequence_Fast_GET_ITEM(fast_now_tzinfos, tr_index);
                Py_INCREF(fast_now_tzinfo);
                break;
            }

            pre_tr_secs = post_tr_secs;
        }

    }

    // 2. datetime_from_timet_and_us()
    struct tm tm;
    int year, month, day, hour, minute, second, fold = 0;

    if (_PyTime_localtime(secs, &tm) != 0)
        return NULL;

    year = tm.tm_year + 1900;
    month = tm.tm_mon + 1;
    day = tm.tm_mday;
    hour = tm.tm_hour;
    minute = tm.tm_min;
    second = Py_MIN(59, tm.tm_sec);

    // 3. new_datetime_ex2()
    PyDateTime_DateTime *dt;
    char aware = fast_now_tzinfo != Py_None;

    dt = (PyDateTime_DateTime *) (fast_now_class->tp_alloc(fast_now_class, aware));
    if (dt != NULL) {
        dt->hastzinfo = aware;
        dt->hashcode = -1;
        SET_YEAR(dt, year);
        SET_MONTH(dt, month);
        SET_DAY(dt, day);
        DATE_SET_HOUR(dt, hour);
        DATE_SET_MINUTE(dt, minute);
        DATE_SET_SECOND(dt, second);
        DATE_SET_MICROSECOND(dt, usecond);
        if (aware) {
            Py_INCREF(fast_now_tzinfo);
            dt->tzinfo = fast_now_tzinfo;
        }
        DATE_SET_FOLD(dt, fold);
    }

    return (PyObject *)dt;
}

static PyMethodDef FastNowMethods[] = {
    {"init",  fast_now_init, METH_VARARGS, "Initialize the module with some local time informations"},
    {"now",  fast_now_now, METH_NOARGS, "Faster 'now()' method for initialized class"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef fast_now_module = {
    PyModuleDef_HEAD_INIT,
    "fast_now",
    "Faster implementation of '.now()' for the Loguru library",
    -1,
    FastNowMethods
};

PyMODINIT_FUNC
PyInit_fast_now(void)
{
    PyDateTime_IMPORT;
    return PyModule_Create(&fast_now_module);
}
