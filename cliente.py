import requests, json, sys, base64

BASE_URL = "http://localhost:8000"
TOKEN = None
ROL = None

def imprimir_titulo(texto): print(f"\n{'='*45}\n {texto.center(43)} \n{'='*45}")

def get_rol_desde_token(token):
    payload = token.split('.')[1]
    payload += '=' * (-len(payload) % 4)
    return json.loads(base64.b64decode(payload)).get('role')

def req(method, endpoint, payload=None):
    headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    if method == 'POST': return requests.post(f"{BASE_URL}{endpoint}", json=payload, headers=headers)
    return requests.get(f"{BASE_URL}{endpoint}", headers=headers)

def menu_admin_db():
    while True:
        imprimir_titulo("ADMINISTRACIÓN DE BD")
        print("1. Crear BD\n2. Listar BDs\n3. Eliminar BD\n4. Crear Tabla\n5. Listar Tablas\n6. Eliminar Tabla\n7. Regresar")
        op = input("\nElige: ")
        
        db = input("Nombre BD: ") if op in ['1','3','4','5','6'] else ""
        tb = input("Nombre Tabla: ") if op in ['4','6'] else ""
        
        if op == '1': print(req('POST', '/admin/create_db', {"db_name": db, "table_name": ""}).json())
        elif op == '2': print(req('POST', '/admin/list_db', {"db_name": "", "table_name": ""}).json())
        elif op == '3': print(req('POST', '/admin/delete_db', {"db_name": db, "table_name": ""}).json())
        elif op == '4': print(req('POST', '/admin/create_table', {"db_name": db, "table_name": tb}).json())
        elif op == '5': print(req('POST', '/admin/list_table', {"db_name": db, "table_name": ""}).json())
        elif op == '6': print(req('POST', '/admin/delete_table', {"db_name": db, "table_name": tb}).json())
        elif op == '7': break

def menu_nosql():
    while True:
        imprimir_titulo(f"NoSQL JSON (Permisos: {ROL.upper()})")
        print("1. Buscar")
        if ROL in ['admin', 'escritor']: print("2. Insertar\n3. Actualizar\n4. Eliminar")
        print("5. Regresar")
        
        op = input("\nElige: ")
        if op == '5': break
        
        db = input("Base de datos: ")
        tb = input("Tabla: ")
        
        try:
            if op == '1': 
                print(req('POST', '/find', {"db_name": db, "table_name": tb}).json())
            elif op == '2' and ROL in ['admin', 'escritor']:
                data = json.loads(input("JSON> "))
                print(req('POST', '/insert', {"db_name": db, "table_name": tb, "data": data}).json())
            elif op == '3' and ROL in ['admin', 'escritor']:
                ck = input("Condición Llave: "); cv = input("Condición Valor: "); nd = json.loads(input("Nuevo JSON> "))
                print(req('POST', '/update', {"db_name": db, "table_name": tb, "condition_key": ck, "condition_value": cv, "new_data": nd}).json())
            elif op == '4' and ROL in ['admin', 'escritor']:
                ck = input("Condición Llave: "); cv = input("Condición Valor: ")
                print(req('POST', '/delete', {"db_name": db, "table_name": tb, "condition_key": ck, "condition_value": cv}).json())
            else: print("[-] Opción o permiso denegado.")
        except Exception as e: print(f"[-] Error: {e}")

def main():
    global TOKEN, ROL
    while True:
        if not TOKEN:
            imprimir_titulo("BIENVENIDO AL SISTEMA DBaaS")
            # AQUÍ ESTÁ LA NUEVA OPCIÓN
            print("1. Iniciar Sesión\n2. Registrarse (Crear Cuenta Principal)\n3. Salir")
            op_ini = input("\nElige: ")
            
            if op_ini == '1':
                res = req('POST', '/login', {"username": input("Usuario: "), "password": input("Pass: ")})
                if res.status_code == 200: 
                    TOKEN = res.json().get("token")
                    ROL = get_rol_desde_token(TOKEN)
                else: print("[-] Error de Login")
            elif op_ini == '2':
                u = input("Nuevo Usuario: ")
                p = input("Contraseña: ")
                res = req('POST', '/register_public', {"username": u, "password": p})
                if res.status_code == 200: 
                    print("\n[+] Cuenta creada con éxito. Ya puedes iniciar sesión con tu nuevo usuario.")
                else: 
                    print(f"\n[-] Error: {res.json().get('detail')}")
            else: sys.exit()
            
        else:
            imprimir_titulo(f"MENÚ PRINCIPAL ({ROL.upper()})")
            if ROL == 'admin': print("1. Administración BD\n2. Crear Empleado (Lector/Escritor)")
            print("3. Interfaz SQL\n4. Interfaz NoSQL\n5. Consultas (MPI)\n6. Cerrar Sesión")
            
            op = input("\nElige: ")
            
            if op == '1' and ROL == 'admin': menu_admin_db()
            elif op == '2' and ROL == 'admin':
                res = req('POST', '/register', {"username": input("Usuario: "), "password": input("Pass: "), "role": input("Rol (escritor/lector): ")})
                print(res.json())
            elif op == '3':
                q = input("SQL> ")
                print(req('POST', '/sql', {"query": q}).json())
            elif op == '4': menu_nosql()
            elif op == '5':
                print(req('POST', '/query', {"db_name": input("BD: "), "table_name": input("Tabla: "), "operation": input("Operación (COUNT/SUM/JOIN..): ").upper()}).json())
                print("[!] Revisa la consola del Worker.")
            elif op == '6': TOKEN, ROL = None, None

if __name__ == "__main__": main()