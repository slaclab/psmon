import os
import sys
import numpy as np
import collections
from itertools import chain
from contextlib import contextmanager
# For Python 3 - builtin zip returns generator
if sys.version_info < (3,):
    from itertools import izip
else:
    izip = zip


def is_py_iter(obj):
    """
    Check if the object is an iterable python object excluding ndarrays
    """
    return hasattr(obj, '__iter__') and not isinstance(obj, np.ndarray)


def py_length(obj):
    """
    Returns of the length of the object. Always '1' for scalar types
    """
    if isinstance(obj, (collections.Sequence, np.ndarray)):
        return len(obj)
    else:
        return 1


def convert_to_array(obj):
    """
    Converts the object into a numpy array if needed. Scalars become a
    1-dim array
    """
    if isinstance(obj, np.ndarray):
        return obj
    elif isinstance(obj, collections.Sequence):
        return np.array(obj)
    else:
        return np.array([obj])


def check_data(obj):
    """
    Checks that the deepest nested sequence object is a numpy array and
    converts the object if needed.
    """
    if isinstance(obj, collections.Sequence):
        if obj and (isinstance(obj[0], np.ndarray) or isinstance(obj[0], collections.Sequence)):
            return [convert_to_array(sub_obj) for sub_obj in obj]
        else:
            return convert_to_array(obj)
    else:
        return obj


def arg_inflate(index, *args):
    args = list(args)
    for i in range(len(args)):
        if i == index:
            continue
        if not is_py_iter(args[i]):
            args[i] = [args[i]] * len(args[index])
    return args


def arg_inflate_flat(index, *args):
    if is_py_iter(args[index]):
        return list(chain.from_iterable(izip(*arg_inflate(index, *args))))
    else:
        return args


def arg_inflate_tuple(index, *args):
    if is_py_iter(args[index]):
        return zip(*arg_inflate(index, *args))
    else:
        return [args]


def inflate_input(input, input_ref):
    if is_py_iter(input_ref):
        return arg_inflate(1, input, input_ref)[0]
    else:
        return [input]


def make_bins(nbins, bmin, bmax):
    step = (bmax - bmin)/nbins
    return np.arange(bmin, bmax + step, step)[:nbins+1]


def window_ratio(min_res, max_res):
    def window_ratio_calc(ncols, nrows):
        pref_x = min_res.x * ncols
        pref_y = min_res.y * nrows

        if pref_x > max_res.x or pref_y > max_res.y:
            num = min(max_res.x/float(ncols), max_res.y/float(nrows))
            pref_x = max(ncols * num, min_res.x)
            pref_y = max(nrows * num, min_res.y)

        return int(pref_x), int(pref_y)
    return window_ratio_calc


def merge_dicts(base, updates):
    new_dict = base.copy()
    new_dict.update(updates)
    return new_dict


@contextmanager
def redirect_stdout():
    sys.stdout.flush()
    sys.stderr.flush()
    stdoutfd = os.dup(sys.stdout.fileno())
    stderrfd = os.dup(sys.stderr.fileno())
    with open(os.devnull, 'wb') as devnull:
        os.dup2(devnull.fileno(), sys.stdout.fileno())
        os.dup2(devnull.fileno(), sys.stderr.fileno())
        try:
            yield
        finally:
            os.dup2(stdoutfd, sys.stdout.fileno())
            os.dup2(stderrfd, sys.stderr.fileno())
