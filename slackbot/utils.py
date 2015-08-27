#!/usr/bin/env python
# coding: utf-8

from functools import wraps


class ObjectDict(dict):
    """
    retrieve value of dict in dot style
    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError('Has no attribute %s' % key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)

    def __str__(self):
        return '<ObjectDict %s >' % dict(self)


def decorator_factory(before_wrapper=None, before_func=None):
    """Return a decorator which triggers callback in each phase"""
    def decorator(func):
        if before_wrapper:
            before_wrapper(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            if before_func:
                before_func(*args, **kwargs)

            return func(*args, **kwargs)
        return wrapper
    return decorator
