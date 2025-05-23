import tkinter as tk
from tkinter import messagebox, ttk
from vm_manager import list_vms, get_vm_status, start_vm, stop_vm, delete_vm, create_vm


def refresh_vm_list(tree):
    for row in tree.get_children():
        tree.delete(row)
    for domain in list_vms():
        status = get_vm_status(domain)
        tree.insert("", "end", values=(domain.name(), status))

def launch_app():
    root = tk.Tk()
    root.title("Gestor de Máquinas Virtuales")

    tree = ttk.Treeview(root, columns=("Nombre", "Estado"), show="headings")
    tree.heading("Nombre", text="Nombre")
    tree.heading("Estado", text="Estado")
    tree.pack(fill=tk.BOTH, expand=True)

    btn_frame = ttk.Frame(root)
    btn_frame.pack(pady=5)

    def on_start():
        selected = tree.selection()
        if selected:
            name = tree.item(selected[0])['values'][0]
            start_vm(name)
            refresh_vm_list(tree)
    
    def on_stop():
        selected = tree.selection()
        if selected:
            name = tree.item(selected[0])['values'][0]
            stop_vm(name)
            refresh_vm_list(tree)

    def on_delete():
        selected = tree.selection()
        if selected:
            name = tree.item(selected[0])['values'][0]
            delete_vm(name)
            refresh_vm_list(tree)

    def on_create():
        win = tk.Toplevel(root)
        win.title("Crear Máquina Virtual")

        labels = ["Nombre", "Memoria (MB)", "vCPU", "Ruta del Disco"]
        entries = []
        for i, lbl in enumerate(labels):
            tk.Label(win, text=lbl).grid(row=i, column=0)
            ent = tk.Entry(win)
            ent.grid(row=i, column=1)
            entries.append(ent)

        def crear():
            name = entries[0].get()
            memory = int(entries[1].get())
            vcpu = int(entries[2].get())
            disk = entries[3].get()
            create_vm(name, memory, vcpu, disk)
            win.destroy()
            refresh_vm_list(tree)

        tk.Button(win, text="Crear", command=crear).grid(row=4, columnspan=2)

    tk.Button(btn_frame, text="Actualizar", command=lambda: refresh_vm_list(tree)).grid(row=0, column=0, padx=5)
    tk.Button(btn_frame, text="Iniciar", command=on_start).grid(row=0, column=1, padx=5)
    tk.Button(btn_frame, text="Detener", command=on_stop).grid(row=0, column=2, padx=5)
    tk.Button(btn_frame, text="Eliminar", command=on_delete).grid(row=0, column=3, padx=5)
    tk.Button(btn_frame, text="Crear VM", command=on_create).grid(row=0, column=4, padx=5)

    refresh_vm_list(tree)
    root.mainloop()