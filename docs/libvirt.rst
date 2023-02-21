libvirt (experimental)
====

This document describes how VMCloak supports libvirt. Follow the steps
in :ref:`libvirt-networking` before getting started.

Currently all VMs are created with the ``-enable-kvm`` flag.

Dependencies (on Arch-linux):

* libvirt
* qemu-full
* virt-manager 

Python Dependencies:

.. code-block:: bash

   pip install libvirt-python

Setup
-----

To use libvirt one has to be in the libvirt group.
Don't forget to logout and back in after adding the user to the group.

.. code-block:: bash

   sudo gpasswd -a <VMCloak user> libvirt

After adding the user into the libvirt group the service must be started
and if so desired also enabled.

.. code-block:: bash

   sudo systemctl start libvirt.service
   sudo systemctl enable libvirt.service # optional

virt-manager must now be connected to libvirt.
To do so open virt-manager go to file -> "add connection...".
In the opening window set "QEMU/KVM" as a hypervisor and click on connect.

.. _libvirt-networking:

Networking (mandatory steps)
----------------------------

VMCloak creates libvirt VMs using the 'bridge' (`-netdev type=bridge`) network type.
A single bridge interface with its own subnet is needed for this.

One can use the default libvirt interface for this purpose.
To find it open virt-manager and double click QEMU/KVM on the VM list.
In the opening window go to "Virtual Networks".
There you can inspect the network parameters.
As a walk around change the name of the default network to its device name. (ex.: virbr0)
