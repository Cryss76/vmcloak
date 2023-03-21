import yaml
import logging

from pathlib import Path
from proxmoxer import ProxmoxAPI


from vmcloak.remote_platforms.remote_platform_interface import Remote_platform_interface


log = logging.getLogger(__name__)
name = "Proxmox"


class Proxmox(Remote_platform_interface):

    def __init__(self) -> None:
        super().__init__()

        config_file = Path("~/.vmcloak/conf/proxmox.yaml").expanduser()

        if not config_file.is_file():
            log.error("config file does not exists or is not a file")
            exit(1)

        config = yaml.safe_load(config_file.read_text())

        self.host = config["host"]
        self.user = config["user"]
        self.pw = config["pw"]

    def clone(self):
        pass

    def delimg(self):
        pass

    def delvm(self):
        pass

    def init(self, name):
        # TODO:
        # - Upload iso
        # - create VM
        # - Install Windows
        # - stop vm
        vm_name_list = self.get_vm_name_list()

        if name in vm_name_list:
            log.error("VM already exists.")

    def install(self):
        pass

    def modify(self):
        pass

    def snapshot(self):
        pass

    def get_vm_name_list(self):
        # TODO:
        # - support more than one node
        # - support ssl verify
        prox = ProxmoxAPI(self.host, user=self.user,
                          password=self.pw, verify_ssl=False)
    
        node = prox.nodes.get()
        if not node:
            log.error("No nodes in the Server")
            exit(1)
    
        vms = prox.nodes(node[0]["node"]).qemu.get()
        if not vms:
            log.error("Couldnt get vms list")
            exit(1)
        vms = [vm["name"] for vm in vms]
    
        return vms

