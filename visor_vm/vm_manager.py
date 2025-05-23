import libvirt
import xml.etree.ElementTree as ET
from utils import format_vm_state

conn = libvirt.open('qemu:///system')
if conn is None:
    print('No se pudo conectar a la hipervisor')
    exit(1)

def list_vms():
    return conn.listAllDomains()

def get_vm_status(domain):
    state, _ = domain.state()
    return format_vm_state(state)

def start_vm(name):
    dom = conn.lookupByName(name)
    if not dom.isActive():
        dom.create()
        print(f'La máquina virtual {name} ha sido iniciada.')
        return True
    return False

def stop_vm(name):
    dom = conn.lookupByName(name)
    if dom.isActive():
        dom.shutdown()
        print(f'La máquina virtual {name} ha sido detenida.')
        return True
    return False

def delete_vm(name):
    dom = conn.lookupByName(name)
    if dom.isActive():
        dom.destroy()
    dom.undefine()
    print(f'La máquina virtual {name} ha sido eliminada.')
    return True

def create_vm(name, memory, vcpu, disk_path, xml_template_path = "resources/template.xml"):
    with open(xml_template_path, 'r') as file:
        xml_config = file.read()
    xml_config = xml_config.replace("{{NAME}}", name)
    xml_config = xml_config.replace("{{MEMORY}}", str(memory))
    xml_config = xml_config.replace("{{VCPU}}", str(vcpu))
    xml_config = xml_config.replace("{{DISK_PATH}}", disk_path)
    conn.defineXML(xml_config)
    print(f'La máquina virtual {name} ha sido creada.')
    return True