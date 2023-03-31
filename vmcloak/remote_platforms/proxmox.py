import os
import random
import yaml
import logging
import time

from pathlib import Path
from proxmoxer import ProxmoxAPI

from vmcloak.remote_platforms.remote_platform_interface import Remote_platform_interface
from vmcloak.ostype import get_os
from vmcloak.repository import Image
from vmcloak.platforms import Machinery
from vmcloak import remote as remote_rep
from vmcloak.repository import vms_path


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
        self.node = config["node"]
        self.wait = 15

    def clone(self):
        pass

    def delimg(self):
        pass

    def delvm(self):
        pass

    def init(self, name, _, iso_name, attr):
        # TODO:
        # - Upload iso
        # - create VM
        # - Install Windows
        # - stop vm
        vm_name_list = self.get_vm_name_list()

        if name in vm_name_list:
            log.error("VM already exists.")

        self.create_vm(name, iso_name, attr)

    def install(self):
        pass

    def modify(self):
        pass

    def snapshot(self):
        pass

    def create_vm(self, name, iso_name, attr):
        prox = ProxmoxAPI(self.host, user=self.user,
                          password=self.pw, verify_ssl=False)

        vmid = self._get_new_random_vmid(prox)
        attr["vmid"] = vmid

        prox.nodes(self.node).qemu.post(vmid=vmid, memory=attr["ramsize"], cores=attr["cpus"],
                                        cdrom="local:iso/%s,media=cdrom,size=4266330K" % iso_name,
                                        net0="model=e1000,bridge=vmbr0,firewall=1",
                                        sata0="local-lvm:%i,discard=on" % attr["hddsize"],
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

    def save(self, name, attr, session, h, vm):
        log.info("Added image %r to the repository.", name)
        session.add(Image(id=attr["vmid"],
                          name=name,
                          # path=attr["path"],
                          path = "-",
                          osversion=attr["osversion"],
                          servicepack="%s" % h.service_pack,
                          mode="normal",
                          ipaddr=attr["ip"],
                          port=attr["port"],
                          adapter=attr["adapter"],
                          netmask=attr["netmask"],
                          gateway=attr["gateway"],
                          cpus=attr["cpus"],
                          ramsize=attr["ramsize"],
                          vramsize=attr["vramsize"],
                          vm="%s" % vm,
                          # paravirtprovider=attr["paravirtprovider"],
                          mac="-"))
        session.commit()

    @staticmethod
    def start_image_vm(image, _):
        tmp = Proxmox()
        prox = ProxmoxAPI(tmp.host, user=tmp.user,
                          password=tmp.pw, verify_ssl=False)
        prox.nodes(tmp.node).qemu(image.id).status.start.post()

    def get_vm_name_list(self):
        # TODO:
        # - support ssl verify
        prox = ProxmoxAPI(self.host, user=self.user,
                          password=self.pw, verify_ssl=False)
    
        vms = prox.nodes(self.node).qemu.get()
        if vms is None:
            log.error("Couldnt get vms list")
            exit(1)
        vms = [vm["name"] for vm in vms]
    
        return vms

    def wait_for_status(self, id, prox, status):
        while True:
            vm_status = prox.nodes(self.node).qemu(id).status.current.get()
            if vm_status is None:
                continue
            print(vm_status["qmpstatus"])
            if vm_status["qmpstatus"] == status:
                break
            time.sleep(self.wait)

    @staticmethod
    def wait_for_shutdown(name):
        image = remote_rep.find_image(name)
        tmp = Proxmox()
        prox = ProxmoxAPI(tmp.host, user=tmp.user,
                          password=tmp.pw, verify_ssl=False)

        while True:
            vm_status = prox.nodes(tmp.node).qemu(image.id).status.current.get()
            if vm_status is None:
                continue
            if vm_status["qmpstatus"] == "stopped":
                break
            time.sleep(tmp.wait)

    @staticmethod
    def prepare_snapshot(vmname, attr):
        dirpath = Path(f"{vms_path}/{name}")
        dirpath.mkdir(parents=True, exist_ok=True)
        config_file = Path(f"{vms_path}/{name}/{vmname}.yaml")
        attr["path"] = dirpath
        if config_file.is_file():
            return False
        return str(dirpath.absolute())
        # dirpath = os.path.join(vms_path, name, vmname)
        # os.makedirs(dirpath, exist_ok=True, mode=0o775)
        # path = os.path.join(dirpath, vmname, ".yaml")
        # attr["path"] = path
        # if os.path.exists(path):
        #     return False
        # return dirpath

    @staticmethod
    def create_snapshot_vm(image, vmname, attr):
        tmp = Proxmox()
        prox = ProxmoxAPI(tmp.host, user=tmp.user,
                          password=tmp.pw, verify_ssl=False)
        # create random new id
        new_vmid = tmp._get_new_random_vmid(prox)
        attr["vmid"] = new_vmid

        # Check if the given image is a template and turn it to one if necessary
        image_config = prox.nodes(tmp.node).qemu(image.id).config.get()
        if image_config is None:
            log.error("Couldn't get image config information aborting...")
            exit(1)

        # if image_config.get("template") is None:
        #     log.error("Couldn't check image Template status aborting...")
        #     exit(1)

        if not image_config.get("template") == 1:
            prox.nodes(tmp.node).qemu(image.id).template.post()
            time.sleep(tmp.wait)

        prox.nodes(tmp.node).qemu(image.id).clone.post(newid=new_vmid, name=vmname, full=0)
        prox.nodes(tmp.node).qemu(new_vmid).status.start.post()

    @staticmethod
    def create_snapshot(name):
        # TODO:
        #   - get vmid by name
        #   - save yaml file with configs in snapshot dir
        tmp = Proxmox()
        prox = ProxmoxAPI(tmp.host, user=tmp.user,
                          password=tmp.pw, verify_ssl=False)

        # Get vmid from VM list
        vm_list = prox.nodes(tmp.node).qemu.get()
        if vm_list is None:
            log.error("cloudn't get VM List.")
            exit(1)
        try:
            vmid = [vm["vmid"] for vm in vm_list if vm.get("name") == name][0]
        except IndexError:
            log.error(f"VM {name} does not exist.")
            exit(1)

        # Create snapshot, then stop the vm
        prox.nodes(tmp.node).qemu(vmid).status.suspend.post()
        # wait till suspended
        time.sleep(tmp.wait)
        prox.nodes(tmp.node).qemu(vmid).snapshot.post(snapname="vmcloak", vmstate=1)
        # wait?
        # stop the vm!
        time.sleep(tmp.wait)
        prox.nodes(tmp.node).qemu(vmid).status.stop.post()


    @staticmethod
    def create_machineinfo_dump(name, image, attr):
        """Save VM infor intou vmcloak config folder"""
        snapshot_data_file = Path(f"{vms_path}/Proxmox/{name}.yaml")

        snapshot_data = {}
        snapshot_data["vmname"] = name
        snapshot_data["snapshot_name"] = "vmcloak"
        snapshot_data["ip"] = attr["ip"]
        snapshot_data["os"] = image.osversion

        snapshot_data_file.write_text(yaml.dump(snapshot_data))

    @staticmethod
    def remove_vm_data(_):
        """For compatibility purpose only"""
        pass

    class VM(Machinery):
        """Only exists for compatibility purposes"""
        def attach_iso(self, _):
            pass

        def detach_iso(self, _):
            pass

    def _get_new_random_vmid(self, prox) -> int:
        while True:
            vmid = random.randint(100, 999_999_999)
            vm_list = prox.nodes(self.node).qemu.get()
            if vm_list is None:
                log.error("Couldnt get vm list")
                quit(1)
            vm_list = [vm["vmid"] for vm in vm_list]
            if not vmid in vm_list:
                break
        return vmid

