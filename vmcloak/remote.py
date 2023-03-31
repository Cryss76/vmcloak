from sys import modules

from vmcloak.repository import Image, Session


def platform(name):
    full = 'vmcloak.remote_platforms.' + name
    m = modules.get(full)
    if not m:
        m = __import__(full)
        m = getattr(m.remote_platforms, name)
    m = getattr(m, m.name)

    return m


def find_image(name):
    session = Session()
    return session.query(Remote_Image).filter_by(name=name).first()


class Remote_Image(Image):
    @property
    def platform(self):
        return platform(self.vm)

