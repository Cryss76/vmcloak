import logging
import yaml
from proxmoxer import ProxmoxAPI
from pathlib import Path

from vmcloak.abstract import Platform, VirtualDrive
from vmcloak.repository import IPNet

log = logging.getLogger(__name__)


def _create_template_config_file(path: Path) -> None:
    """Ensure the config file exists."""
    config = {}
    config["host"] = "Your hosts ip"
    config["user"] = "User to login as"
    config["pw"] = "Password to login with"
    config["node"] = "The node where the vm(s) will be hosted"
    config["sr"] = "Storage repository where the iso for image creation is."
    config["default_net"] = "192.168.1.0/24 for example"

    config_file = yaml.dump(config)
    path.write_text(config_file)


class proxmox(Platform):
    name = "Proxmox"

    def __init__(self) -> None:
        super().__init__()

        config_file = Path("~/.vmcloak/conf/proxmox.yaml").expanduser()
        if not config_file.is_file():
            log.error("No configuration file found.")
            log.info("Creating configuration template for Proxmox...")
            _create_template_config_file(config_file)
            log.info("Aborting please setup the config file.")
            exit(1)

        config = yaml.safe_load(config_file.read_text())
        self.host = config["host"]
        self.user = config["user"]
        self.pw = config["pw"]
        self.node = config["node"]
        self.sr = config["sr"]
        self.net = config["default_net"]
        self.wait = 15

    @property
    def default_net(self) -> IPNet:
        if not self._default_net:
            self._default_net = IPNet(self.net)
        return self._default_net


class ProxmoxDrive(VirtualDrive):
    pass
