import logging
import yaml
import random
import time
from proxmoxer import ProxmoxAPI
from pathlib import Path

from vmcloak.abstract import Platform, VirtualDrive
from vmcloak.repository import IPNet, Image, image_path
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
        self._connection = None

    @property
    def default_net(self) -> IPNet:
        if not self._default_net:
            self._default_net = IPNet(self.net)
        return self._default_net

    def create_new_image(self, name: str, _, iso_path: str, attr: dict
                         ) -> None:
        attr["path"] = f"{attr['path']}/proxmox/{name}.yml"
        vm_config_file = Path(attr["path"])
        if vm_config_file.exists():
            raise ValueError("Image %s already exists" % attr["path"])

        vmid = self._get_new_random_vmid(self.prox)
        self.prox.nodes(self.node).qemu.post(
            vmid=vmid, memory=attr["ramsize"],
            cores=attr["cpus"],
            cdrom=f"local:iso/{iso_path},media=cdrom,size=4266330K",
            net0="model=e1000,bridge=vmbr0,firewall=1",
            sata0=self.sr + ":%i,discard=on" % attr["hddsize"],
            ostype=get_os(attr["osversion"]).name,
            name=name)

        self.prox.nodes(self.node).qemu(vmid).status.start.post()
        time.sleep(self.wait)

        running = True
        while running:
            vm_status = self.prox.nodes(self.node).qemu(
                vmid).status.current.get()
            if vm_status is None:
                continue
            if vm_status["qmpstatus"] == "stopped":
                running = False
            time.sleep(self.wait)

        vm_config = yaml.dump({"vmid": vmid})
        vm_config_file.write_text(vm_config)

        attr["mac"] = ""

    def remove_img(self, image: Image) -> None:
        log.info("Removing image %s", image.path)

        vm_config_file = Path(image.path)
        vmid = yaml.safe_load(vm_config_file.read_text())["vmid"]

        self.prox.nodes(self.node).qemu(vmid).delete()

        vm_config_file.unlink()

    def clone_disk(self, image: Image, target: str) -> None:
        config_file = Path(f"{image_path}/proxmox/{target}.yml")
        if config_file.exists():
            log.error(f"Outpath: {config_file} already exists.")
            exit(1)

        log.info("Cloning %s to %s", image.name, target)

        oldvmid = yaml.safe_load(Path(image.path).read_text())["vmid"]

        new_vmid = self._get_new_random_vmid(self.prox)
        self.prox.nodes(self.node).qemu(oldvmid).clone.post(
            newid=new_vmid, name=target)

        config_file.write_text(yaml.dump({"vmid": new_vmid}))

        image.path = f"{config_file}"

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

    @property
    def prox(self):
        if self._connection:
            try:
                self._connection.nodes(self.node).status.get()
            except Exception:
                # fine beacause of the following reconnect with ProxmoxAPI
                pass
            else:
                return self._connection

        self._connection = ProxmoxAPI(self.host, user=self.user,
                                      password=self.pw, verify_ssl=False)
        return self._connection


class ProxmoxDrive(VirtualDrive):
    pass
