from sys import modules


def platform(name: str):
    full = 'vmcloak.remote_platforms.' + name
    m = modules.get(full)
    if not m:
        m = __import__(full)
        m = getattr(m.remote_platforms, name)
        m = getattr(m, m.name)

    return m

