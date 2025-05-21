import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import libvirt
import os
import xml.etree.ElementTree as ET
import subprocess
from datetime import datetime

class LibvirtManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Máquinas Virtuales con Libvirt")
        self.root.geometry("1000x700")
        
        # Conexión a libvirt
        self.conn = None
        self.connect_to_libvirt()
        
        if self.conn is None:
            messagebox.showerror("Error", "No se pudo conectar a libvirt")
            self.root.destroy()
            return

    def show_connection_error(self, title, message):
        """Mostrar un mensaje de error de conexión y cerrar la aplicación"""
        messagebox.showerror(title, message)
        self.root.destroy()
        # Variables de estado
        self.vm_templates = {
            "Linux Básico": self.get_linux_template(),
            "Windows Básico": self.get_windows_template(),
            "Servidor": self.get_server_template()
        }
        
        # Crear la interfaz
        self.create_widgets()
        self.refresh_vm_list()
    
    def connect_to_libvirt(self):
        """Conectar al hipervisor libvirt"""
        try:
            socket_path = "/var/run/libvirt/libvirt-sock"
            if not os.path.exists(socket_path):
                self.show_connection_error(
                    "El socket de libvirt no existe",
                    "Por favor verifica que el servicio libvirt esté instalado y corriendo.\n"
                    "Puedes iniciarlo con:\n"
                    "sudo systemctl start libvirtd"
                )
                return
            if not os.access(socket_path, os.R_OK | os.W_OK):
                self.show_connection_error(
                    "Problema de permisos",
                    "El usuario no tiene permisos para acceder al socket de libvirt.\n"
                    "Puedes agregar tu usuario al grupo libvirt con:\n"
                    "sudo usermod -aG libvirt $(whoami)\n"
                    "Luego cierra sesión y vuelve a ingresar."
                )
                return
            self.conn = libvirt.open("qemu:///session")
            if self.conn is None:
                messagebox.showerror("Error", "No se pudo conectar a libvirt")
                self.root.destroy()
        except libvirt.libvirtError as e:
            messagebox.showerror("Error", f"Error de libvirt: {e}")
            self.root.destroy()
    
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel superior con botones de acción
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="Nueva VM", command=self.show_create_vm_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Iniciar VM", command=self.start_vm).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Detener VM", command=self.stop_vm).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Reiniciar VM", command=self.reboot_vm).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Eliminar VM", command=self.delete_vm).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Actualizar", command=self.refresh_vm_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Consola", command=self.open_console).pack(side=tk.LEFT, padx=5)
        
        # Treeview para mostrar las VMs
        self.tree = ttk.Treeview(main_frame, columns=('name', 'status', 'memory', 'vcpus', 'os'), show='headings')
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Configurar columnas
        self.tree.heading('name', text='Nombre')
        self.tree.heading('status', text='Estado')
        self.tree.heading('memory', text='Memoria (MB)')
        self.tree.heading('vcpus', text='vCPUs')
        self.tree.heading('os', text='Sistema Operativo')
        
        # Barra de desplazamiento
        scrollbar = ttk.Scrollbar(self.tree, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Panel de información detallada
        info_frame = ttk.LabelFrame(main_frame, text="Información detallada", padding="10")
        info_frame.pack(fill=tk.X, pady=10)
        
        self.info_text = tk.Text(info_frame, height=8, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # Configurar evento de selección
        self.tree.bind('<<TreeviewSelect>>', self.show_vm_details)
    
    def refresh_vm_list(self):
        """Actualizar la lista de máquinas virtuales"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            # Obtener todas las máquinas virtuales (activas e inactivas)
            active_vms = self.conn.listAllDomains(libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE)
            inactive_vms = self.conn.listAllDomains(libvirt.VIR_CONNECT_LIST_DOMAINS_INACTIVE)
            
            all_vms = active_vms + inactive_vms
            
            for vm in all_vms:
                name = vm.name()
                status = "Activa" if vm.isActive() else "Inactiva"
                info = vm.info()
                memory = info[1] // 1024  # Convertir a MB
                vcpus = info[3]
                os_type = vm.OSType()
                
                self.tree.insert('', tk.END, values=(name, status, memory, vcpus, os_type))
        except libvirt.libvirtError as e:
            messagebox.showerror("Error", f"No se pudo obtener la lista de VMs: {e}")
    
    def show_vm_details(self, event):
        """Mostrar detalles de la VM seleccionada"""
        selected_item = self.tree.focus()
        if not selected_item:
            return
        
        item_data = self.tree.item(selected_item)
        vm_name = item_data['values'][0]
        
        try:
            vm = self.conn.lookupByName(vm_name)
            info = vm.info()
            
            details = f"Nombre: {vm.name()}\n"
            details += f"Estado: {'Activa' if vm.isActive() else 'Inactiva'}\n"
            details += f"ID: {vm.ID() if vm.isActive() else 'N/A'}\n"
            details += f"Memoria: {info[1] // 1024} MB\n"
            details += f"vCPUs: {info[3]}\n"
            details += f"Tiempo de CPU: {info[4]} ns\n"
            details += f"Tipo de SO: {vm.OSType()}\n"
            
            # Información de XML
            xml_desc = vm.XMLDesc(0)
            root = ET.fromstring(xml_desc)
            
            # Obtener información de almacenamiento
            disks = root.findall('.//disk')
            details += "\nDiscos:\n"
            for disk in disks:
                if disk.get('device') == 'disk':
                    source = disk.find('.//source')
                    if source is not None:
                        details += f"  - {source.get('file')}\n"
            
            # Información de red
            interfaces = root.findall('.//interface')
            details += "\nInterfaces de red:\n"
            for interface in interfaces:
                mac = interface.find('.//mac')
                source = interface.find('.//source')
                if mac is not None and source is not None:
                    details += f"  - MAC: {mac.get('address')}, Red: {source.get('network') or source.get('bridge')}\n"
            
            self.info_text.config(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, details)
            self.info_text.config(state=tk.DISABLED)
            
        except libvirt.libvirtError as e:
            self.info_text.config(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, f"Error al obtener detalles: {e}")
            self.info_text.config(state=tk.DISABLED)
    
    def show_create_vm_dialog(self):
        """Mostrar diálogo para crear nueva VM"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Crear Nueva Máquina Virtual")
        dialog.geometry("500x600")
        dialog.resizable(False, False)
        
        # Variables del formulario
        name_var = tk.StringVar()
        template_var = tk.StringVar(value="Linux Básico")
        memory_var = tk.IntVar(value=1024)
        vcpus_var = tk.IntVar(value=1)
        storage_var = tk.IntVar(value=10)
        iso_path_var = tk.StringVar()
        
        # Formulario
        ttk.Label(dialog, text="Nombre de la VM:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dialog, textvariable=name_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(dialog, text="Plantilla:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Combobox(dialog, textvariable=template_var, values=list(self.vm_templates.keys())).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(dialog, text="Memoria (MB):").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Spinbox(dialog, textvariable=memory_var, from_=512, to=16384, increment=512).grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(dialog, text="vCPUs:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Spinbox(dialog, textvariable=vcpus_var, from_=1, to=16).grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(dialog, text="Almacenamiento (GB):").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Spinbox(dialog, textvariable=storage_var, from_=5, to=500).grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(dialog, text="Imagen ISO (opcional):").grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dialog, textvariable=iso_path_var).grid(row=5, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(dialog, text="Examinar...", command=lambda: self.browse_iso(iso_path_var)).grid(row=5, column=2, padx=5, pady=5)
        
        # Botones
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Crear", command=lambda: self.create_vm(
            name_var.get(),
            template_var.get(),
            memory_var.get(),
            vcpus_var.get(),
            storage_var.get(),
            iso_path_var.get(),
            dialog
        )).pack(side=tk.RIGHT, padx=5)
    
    def browse_iso(self, iso_path_var):
        """Seleccionar archivo ISO"""
        filename = filedialog.askopenfilename(
            title="Seleccionar imagen ISO",
            filetypes=(("Archivos ISO", "*.iso"), ("Todos los archivos", "*.*"))
        )
        if filename:
            iso_path_var.set(filename)
    
    def create_vm(self, name, template, memory, vcpus, storage_gb, iso_path, dialog):
        """Crear una nueva máquina virtual"""
        if not name:
            messagebox.showerror("Error", "El nombre de la VM es requerido")
            return
        
        try:
            # Obtener la plantilla seleccionada
            xml_template = self.vm_templates.get(template, self.get_linux_template())
            
            # Personalizar la plantilla
            xml_template = xml_template.replace("{{VM_NAME}}", name)
            xml_template = xml_template.replace("{{MEMORY}}", str(memory))
            xml_template = xml_template.replace("{{VCPUS}}", str(vcpus))
            
            # Crear disco de almacenamiento
            storage_path = f"/var/lib/libvirt/images/{name}.qcow2"
            if not os.path.exists(storage_path):
                storage_size = storage_gb * 1024 * 1024 * 1024  # Convertir a bytes
                subprocess.run([
                    'qemu-img', 'create', '-f', 'qcow2',
                    storage_path, str(storage_size)
                ], check=True)
            
            xml_template = xml_template.replace("{{DISK_PATH}}", storage_path)
            
            # Configurar ISO si se proporcionó
            if iso_path and os.path.exists(iso_path):
                xml_template = xml_template.replace("{{ISO_PATH}}", iso_path)
            else:
                # Eliminar el dispositivo CDROM si no hay ISO
                root = ET.fromstring(xml_template)
                for disk in root.findall('.//disk'):
                    if disk.get('device') == 'cdrom':
                        root.find('.//devices').remove(disk)
                xml_template = ET.tostring(root, encoding='unicode')
            
            # Crear la VM
            vm = self.conn.defineXML(xml_template)
            if vm is None:
                messagebox.showerror("Error", "No se pudo crear la VM")
                return
            
            messagebox.showinfo("Éxito", f"Máquina virtual '{name}' creada exitosamente")
            dialog.destroy()
            self.refresh_vm_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la VM: {e}")
    
    def get_selected_vm(self):
        """Obtener la VM seleccionada"""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Por favor selecciona una máquina virtual")
            return None
        
        item_data = self.tree.item(selected_item)
        vm_name = item_data['values'][0]
        
        try:
            return self.conn.lookupByName(vm_name)
        except libvirt.libvirtError as e:
            messagebox.showerror("Error", f"No se pudo encontrar la VM: {e}")
            return None
    
    def start_vm(self):
        """Iniciar la VM seleccionada"""
        vm = self.get_selected_vm()
        if vm is None:
            return
        
        try:
            if vm.isActive():
                messagebox.showinfo("Información", "La máquina virtual ya está en ejecución")
                return
            
            if vm.create() == -1:
                messagebox.showerror("Error", "No se pudo iniciar la máquina virtual")
            else:
                messagebox.showinfo("Éxito", "Máquina virtual iniciada")
                self.refresh_vm_list()
                
        except libvirt.libvirtError as e:
            messagebox.showerror("Error", f"No se pudo iniciar la VM: {e}")
    
    def stop_vm(self):
        """Detener la VM seleccionada"""
        vm = self.get_selected_vm()
        if vm is None:
            return
        
        try:
            if not vm.isActive():
                messagebox.showinfo("Información", "La máquina virtual ya está detenida")
                return
            
            if vm.destroy() == -1:
                messagebox.showerror("Error", "No se pudo detener la máquina virtual")
            else:
                messagebox.showinfo("Éxito", "Máquina virtual detenida")
                self.refresh_vm_list()
                
        except libvirt.libvirtError as e:
            messagebox.showerror("Error", f"No se pudo detener la VM: {e}")
    
    def reboot_vm(self):
        """Reiniciar la VM seleccionada"""
        vm = self.get_selected_vm()
        if vm is None:
            return
        
        try:
            if not vm.isActive():
                messagebox.showinfo("Información", "La máquina virtual está detenida, no se puede reiniciar")
                return
            
            if vm.reboot(0) == -1:
                messagebox.showerror("Error", "No se pudo reiniciar la máquina virtual")
            else:
                messagebox.showinfo("Éxito", "Máquina virtual reiniciada")
                self.refresh_vm_list()
                
        except libvirt.libvirtError as e:
            messagebox.showerror("Error", f"No se pudo reiniciar la VM: {e}")
    
    def delete_vm(self):
        """Eliminar la VM seleccionada"""
        vm = self.get_selected_vm()
        if vm is None:
            return
        
        confirm = messagebox.askyesno(
            "Confirmar",
            f"¿Estás seguro de eliminar la máquina virtual '{vm.name()}'?\nEsta acción no se puede deshacer."
        )
        if not confirm:
            return
        
        try:
            # Obtener información de almacenamiento antes de eliminar
            xml_desc = vm.XMLDesc(0)
            root = ET.fromstring(xml_desc)
            disks = root.findall('.//disk')
            storage_paths = []
            
            for disk in disks:
                if disk.get('device') == 'disk':
                    source = disk.find('.//source')
                    if source is not None:
                        storage_paths.append(source.get('file'))
            
            # Eliminar la VM
            if vm.isActive():
                vm.destroy()
            
            if vm.undefine() == -1:
                messagebox.showerror("Error", "No se pudo eliminar la máquina virtual")
            else:
                # Opcional: eliminar los archivos de almacenamiento
                for path in storage_paths:
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except OSError as e:
                            print(f"No se pudo eliminar {path}: {e}")
                
                messagebox.showinfo("Éxito", "Máquina virtual eliminada")
                self.refresh_vm_list()
                
        except libvirt.libvirtError as e:
            messagebox.showerror("Error", f"No se pudo eliminar la VM: {e}")
    
    def open_console(self):
        """Abrir consola de la VM seleccionada"""
        vm = self.get_selected_vm()
        if vm is None:
            return
        
        try:
            if not vm.isActive():
                messagebox.showinfo("Información", "La máquina virtual debe estar en ejecución para abrir la consola")
                return
            
            # Usar virt-viewer si está disponible
            try:
                subprocess.Popen(['virt-viewer', '-c', 'qemu:///system', vm.name()])
            except FileNotFoundError:
                # Alternativa: usar remote-viewer
                try:
                    subprocess.Popen(['remote-viewer', f"qemu:///system?name={vm.name()}"])
                except FileNotFoundError:
                    messagebox.showwarning(
                        "Advertencia",
                        "No se encontró virt-viewer ni remote-viewer.\n"
                        "Instala virt-viewer para acceder a la consola gráfica."
                    )
        
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la consola: {e}")
    
    def get_linux_template(self):
        """Plantilla XML para una VM Linux básica"""
        return """<domain type='kvm'>
  <name>{{VM_NAME}}</name>
  <memory unit='KiB'>{{MEMORY}}</memory>
  <currentMemory unit='KiB'>{{MEMORY}}</currentMemory>
  <vcpu placement='static'>{{VCPUS}}</vcpu>
  <os>
    <type arch='x86_64' machine='pc-i440fx-2.11'>hvm</type>
    <boot dev='hd'/>
    <boot dev='cdrom'/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <vmport state='off'/>
  </features>
  <cpu mode='host-model' check='partial'/>
  <clock offset='utc'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <pm>
    <suspend-to-mem enabled='no'/>
    <suspend-to-disk enabled='no'/>
  </pm>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{{DISK_PATH}}'/>
      <target dev='vda' bus='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x0'/>
    </disk>
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='{{ISO_PATH}}'/>
      <target dev='hda' bus='ide'/>
      <readonly/>
      <address type='drive' controller='0' bus='0' target='0' unit='0'/>
    </disk>
    <controller type='usb' index='0' model='ich9-ehci1'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x05' function='0x7'/>
    </controller>
    <controller type='pci' index='0' model='pci-root'/>
    <controller type='ide' index='0'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x1'/>
    </controller>
    <controller type='virtio-serial' index='0'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x06' function='0x0'/>
    </controller>
    <interface type='network'>
      <mac address='52:54:00:00:00:00'/>
      <source network='default'/>
      <model type='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
    </interface>
    <serial type='pty'>
      <target type='isa-serial' port='0'>
        <model name='isa-serial'/>
      </target>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <channel type='unix'>
      <target type='virtio' name='org.qemu.guest_agent.0'/>
      <address type='virtio-serial' controller='0' bus='0' port='1'/>
    </channel>
    <input type='tablet' bus='usb'>
      <address type='usb' bus='0' port='1'/>
    </input>
    <input type='mouse' bus='ps2'/>
    <input type='keyboard' bus='ps2'/>
    <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'>
      <listen type='address' address='0.0.0.0'/>
    </graphics>
    <video>
      <model type='qxl' ram='65536' vram='65536' vgamem='16384' heads='1' primary='yes'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
    </video>
    <memballoon model='virtio'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x08' function='0x0'/>
    </memballoon>
  </devices>
</domain>"""
    
    def get_windows_template(self):
        """Plantilla XML para una VM Windows básica"""
        template = self.get_linux_template()
        # Modificar para mejor compatibilidad con Windows
        template = template.replace("<cpu mode='host-model' check='partial'/>", 
                                  "<cpu mode='host-passthrough' check='none'/>")
        template = template.replace("<model type='qxl'", "<model type='cirrus'")
        return template
    
    def get_server_template(self):
        """Plantilla XML para una VM de servidor"""
        template = self.get_linux_template()
        # Añadir configuración adicional para servidores
        template = template.replace("<vcpu placement='static'>{{VCPUS}}</vcpu>",
                                  "<vcpu placement='static'>{{VCPUS}}</vcpu>\n"
                                  "  <numatune>\n"
                                  "    <memory mode='strict' nodeset='0'/>\n"
                                  "  </numatune>")
        return template

if __name__ == "__main__":
    root = tk.Tk()
    app = LibvirtManager(root)
    root.mainloop()