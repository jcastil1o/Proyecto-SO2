def format_vm_state(state_code):
    states = {
        0: "No iniciada",
        1: "Ejecutando",
        2: "Pausada",
        3: "En espera",
        4: "Terminada",
        5: "Cerrada",
        6: "Desconocida"
    }
    return states.get(state_code, "Estado desconocido")
