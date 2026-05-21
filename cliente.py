import sys
import os
import grpc
import json

ruta_protos = os.path.abspath(os.path.join(os.path.dirname(__file__), 'protos'))
sys.path.append(ruta_protos)

import orquestador_pb2, orquestador_pb2_grpc

TOKEN = None
ROL = None
USUARIO = None

def imprimir_titulo(texto): 
    print(f"\n{'='*45}\n {texto.center(43)} \n{'='*45}")

def enviar_comando_crudo(canal, tipo, comando):
    cliente = orquestador_pb2_grpc.ServicioOrquestadorStub(canal)
    peticion = orquestador_pb2.PeticionComandoOrquestador(token=TOKEN, tipo=tipo, comando=comando)
    respuesta = cliente.EnviarComando(peticion)
    
    if respuesta.exito:
        print(f"[EXITO] {respuesta.mensaje}")
        if respuesta.resultado:
            print(f"Resultado:\n{respuesta.resultado}")
    else:
        print(f"{respuesta.mensaje}")

def menu_admin_db(canal):
    while True:
        imprimir_titulo("ADMINISTRACION DE BD")
        print("1. Crear BD\n2. Listar BDs\n3. Eliminar BD")
        print("4. Crear Tabla\n5. Eliminar Tabla\n6. Regresar")
        op = input("\nElige: ")
        
        if op == '6': break
        
        db = input("Nombre BD: ") if op in ['1','3','4','5'] else ""
        tb = input("Nombre Tabla: ") if op in ['4','5'] else ""
        
        if op == '1': enviar_comando_crudo(canal, "SQL", f"CREATE DATABASE {db}")
        elif op == '2': enviar_comando_crudo(canal, "SQL", "SHOW DATABASES")
        elif op == '3': enviar_comando_crudo(canal, "SQL", f"DROP DATABASE {db}")
        elif op == '4': enviar_comando_crudo(canal, "SQL", f"CREATE TABLE {db}.{tb}")
        elif op == '5': enviar_comando_crudo(canal, "SQL", f"DROP TABLE {db}.{tb}")
        else: print("[ERROR] Opcion invalida.")

def menu_nosql(canal):
    while True:
        imprimir_titulo(f"NoSQL JSON (Permisos: {ROL.upper()})")
        print("1. Buscar")
        if ROL in ['administrador', 'usuario_escritura']: 
            print("2. Insertar\n3. Actualizar\n4. Eliminar")
        print("5. Regresar")
        
        op = input("\nElige: ")
        if op == '5': break
        
        db = input("Base de datos: ")
        tb = input("Tabla: ")
        
        try:
            if op == '1':
                cmd = json.dumps({"db": db, "tabla": tb, "accion": "buscar", "datos": {}})
                enviar_comando_crudo(canal, "JSON", cmd)
                
            elif op == '2' and ROL in ['administrador', 'usuario_escritura']:
                data = json.loads(input("JSON a insertar (ej. {\"id\": 1, \"nombre\": \"A\"})> "))
                cmd = json.dumps({"db": db, "tabla": tb, "accion": "insertar", "datos": data})
                enviar_comando_crudo(canal, "JSON", cmd)
                
            elif op == '3' and ROL in ['administrador', 'usuario_escritura']:
                ck = input("Condicion Llave (ej. id): ")
                cv = input("Condicion Valor: ")
                cv = int(cv) if cv.isdigit() else cv
                nd = json.loads(input("Nuevos valores JSON (ej. {\"precio\": 200})> "))
                cmd = json.dumps({"db": db, "tabla": tb, "accion": "actualizar", "datos": {"filtro": {ck: cv}, "valores": nd}})
                enviar_comando_crudo(canal, "JSON", cmd)
                
            elif op == '4' and ROL in ['administrador', 'usuario_escritura']:
                ck = input("Condicion Llave: ")
                cv = input("Condicion Valor: ")
                cv = int(cv) if cv.isdigit() else cv
                cmd = json.dumps({"db": db, "tabla": tb, "accion": "eliminar", "datos": {ck: cv}})
                enviar_comando_crudo(canal, "JSON", cmd)
                
            else: 
                print("[ERROR] Opcion o permiso denegado.")
        except Exception as e: 
            print(f"[ERROR] JSON mal formado: {e}")

def consola_sql(canal):
    print("\n--- CONSOLA SQL ---")
    print("Escribe 'volver' para salir.")
    while True:
        comando = input(f"{USUARIO}@SQL> ")
        if comando.lower() == 'volver': break
        if comando.strip(): enviar_comando_crudo(canal, "SQL", comando)

def main():
    global TOKEN, ROL, USUARIO
    with grpc.insecure_channel('localhost:50050') as canal:
        cliente = orquestador_pb2_grpc.ServicioOrquestadorStub(canal)
        
        while True:
            if not TOKEN:
                imprimir_titulo("BIENVENIDO AL SISTEMA DBaaS")
                print("1. Iniciar Sesion\n2. Registrarse (Crear cuenta principal)\n3. Salir")
                op_ini = input("\nElige: ")
                
                if op_ini == '1':
                    u = input("Usuario: ")
                    p = input("Contrasena: ")
                    res = cliente.Login(orquestador_pb2.PeticionLoginOrquestador(usuario=u, password=p))
                    if res.exito:
                        TOKEN = res.token
                        ROL = res.rol
                        USUARIO = u
                        print(f"[INFO] Autenticacion correcta.")
                    else: print(f"[ERROR] {res.mensaje}")
                    
                elif op_ini == '2':
                    print("\n--- NUEVA CUENTA DE ADMINISTRADOR ---")
                    u = input("Nuevo Usuario: ")
                    p = input("Contrasena: ")
                    res = cliente.Registro(orquestador_pb2.PeticionRegistroOrquestador(usuario=u, password=p, rol="administrador", creador=""))
                    print(f"[EXITO] {res.mensaje}" if res.exito else f"[ERROR] {res.mensaje}")
                elif op_ini == '3': sys.exit()
                
            else:
                imprimir_titulo(f"MENU PRINCIPAL ({ROL.upper()})")
                
                if ROL == 'administrador': 
                    print("1. Administracion de BD")
                    print("2. Registrar Trabajador (Lectura/Escritura)")
                    print("3. Interfaz SQL libre")
                    print("4. Interfaz NoSQL guiada")
                    print("5. Cerrar Sesion")
                else:
                    print("1. Interfaz SQL libre")
                    print("2. Interfaz NoSQL guiada")
                    print("3. Cerrar Sesion")
                
                op = input("\nElige: ")
                
                if op == '1' and ROL == 'administrador': 
                    menu_admin_db(canal)
                elif op == '2' and ROL == 'administrador':
                    print("\n--- REGISTRAR TRABAJADOR ---")
                    emp_u = input("Usuario del trabajador: ")
                    emp_p = input("Contrasena: ")
                    print("Roles: 1. Escritura | 2. Lectura")
                    r_opc = input("Selecciona el numero: ")
                    rol_emp = "usuario_escritura" if r_opc == "1" else "usuario_lectura"
                    
                    res = cliente.Registro(orquestador_pb2.PeticionOrquestador(
                        usuario=emp_u, 
                        password=emp_p, 
                        rol=rol_emp, 
                        creador=USUARIO
                    ))
                    print(f"[EXITO] {res.mensaje}" if res.exito else f"[ERROR] {res.mensaje}")
                elif (op == '3' and ROL == 'administrador') or (op == '1' and ROL != 'administrador'): 
                    consola_sql(canal)
                elif (op == '4' and ROL == 'administrador') or (op == '2' and ROL != 'administrador'): 
                    menu_nosql(canal)
                elif (op == '5' and ROL == 'administrador') or (op == '3' and ROL != 'administrador'): 
                    TOKEN, ROL, USUARIO = None, None, None
                    print("[INFO] Sesion cerrada.")

if __name__ == "__main__":
    main()