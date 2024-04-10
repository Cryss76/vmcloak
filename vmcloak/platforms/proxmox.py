import logging
import yaml
import random
import time
from proxmoxer import ProxmoxAPI
from pathlib import Path

from vmcloak.abstract import Platform, VirtualDrive
from vmcloak.repository import IPNet
from vmcloak.ostype import get_os

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

    def create_new_image(self, name: str, _, iso_path: str, attr: dict
                         ) -> None:
        prox = ProxmoxAPI(self.host, user=self.user, password=self.pw,
                          verify_ssl=False)

        vmid = self._get_new_random_vmid(prox)
        attr["vmid"] = vmid

        prox.nodes(self.node).qemu.post(
            vmid=vmid, memory=attr["ramsize"],
            cores=attr["cpus"],
            cdrom=f"local:iso/{iso_path},media=cdrom,size=4266330K",
            net0="model=e1000,bridge=vmbr0,firewall=1",
            sata0=self.sr + ":%i,discard=on" % attr["hddsize"],
            ostype=get_os(attr["osversion"]).name,
            name=name)

        prox.nodes(self.node).qemu(vmid).status.start.post()
        time.sleep(self.wait)

        running = True
        while running:
            vm_status = prox.nodes(self.node).qemu(vmid).status.current.get()
            if vm_status is None:
                continue
            if vm_status["qmpstatus"] == "stopped":
                running = False
            time.sleep(self.wait)

        attr["mac"] = ""

    def _get_new_random_vmid(self, prox) -> int:
        while True:
            vmid = random.randint(100, 999_999_999)
            vm_list = prox.nodes(self.node).qemu.get()
            if vm_list is None:
                log.error("Couldnt get vm list")
                quit(1)
            vm_list = [vm["vmid"] for vm in vm_list]
            if vmid not in vm_list:
                break
        return vmid


class ProxmoxDrive(VirtualDrive):
    pass
