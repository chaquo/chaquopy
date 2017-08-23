def update_wrapper(wrapper, wrapped):
    """ To be used under python2.4 because functools.update_wrapper() is available only from python2.5+ """
    for attr_name in ('__module__', '__name__', '__doc__'):
        attr_value = getattr(wrapped, attr_name, None)
        if attr_value is not None:
            setattr(wrapper, attr_name, attr_value)
    wrapper.__dict__.update(getattr(wrapped, '__dict__', {}))
    return wrapper
