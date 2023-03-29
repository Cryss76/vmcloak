from abc import ABC, abstractmethod


class Remote_platform_interface(ABC):
    """Provides a generic interface for using remote Platforms."""

    @abstractmethod
    def clone(self):
        raise NotImplemented

    @abstractmethod
    def delimg(self):
        raise NotImplemented

    @abstractmethod
    def delvm(self):
        raise NotImplemented

    @abstractmethod
    def init(self):
        raise NotImplemented

    @abstractmethod
    def install(self):
        raise NotImplemented

    @abstractmethod
    def modify(self):
        raise NotImplemented

    @abstractmethod
    def snapshot(self):
        raise NotImplemented

    @abstractmethod
    def save(self):
        raise NotImplemented

    @abstractmethod
    def start_image_vm(self):
        raise NotImplemented

    @abstractmethod
    def wait_for_shutdown(self):
        raise NotImplemented

    @abstractmethod
    def remove_vm_data(self):
        raise NotImplemented

