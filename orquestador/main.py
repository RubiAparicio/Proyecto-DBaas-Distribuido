import sys
import os
import grpc
import json
import re
import pika
from concurrent import futures

ruta_protos = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'protos'))
sys.path.append(ruta_protos)

import base_datos_pb2, base_datos_pb2_grpc
import metadatos_pb2, metadatos_pb2_grpc
import seguridad_pb2, seguridad_pb2_grpc
import agregacion_pb2, agregacion_pb2_grpc 
import orquestador_pb2, orquestador_pb2_grpc

def mandar_log_asincrono(mensaje):
    try:
        conexion = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        canal = conexion.channel()
        canal.queue_declare(queue='auditoria_dbaas')
        canal.basic_publish(exchange='', routing_key='auditoria_dbaas', body=mensaje)
        conexion.close()
    except Exception:
        pass 

class OrquestadorServidor(orquestador_pb2_grpc.ServicioOrquestadorServicer):

    def Login(self, request, context):
        print(f"[Orquestador] Reenviando intento de login para: {request.usuario}")
        with grpc.insecure_channel('localhost:50053') as canal:
            cliente_auth = seguridad_pb2_grpc.ServicioSeguridadStub(canal)
            res_auth = cliente_auth.IniciarSesion(seguridad_pb2.PeticionLogin(usuario=request.usuario, password=request.password))
            
            rol = ""
            if res_auth.exito:
                res_val = cliente_auth.ValidarToken(seguridad_pb2.PeticionValidacion(token=res_auth.token))
                rol = res_val.rol
                
            return orquestador_pb2.RespuestaLoginOrquestador(
                exito=res_auth.exito, token=res_auth.token, rol=rol, mensaje=res_auth.mensaje
            )

    def Registro(self, request, context):
        print(f"[Orquestador] Reenviando registro para: {request.usuario} creado por {request.creador}")
        with grpc.insecure_channel('localhost:50053') as canal:
            cliente_auth = seguridad_pb2_grpc.ServicioSeguridadStub(canal)
            peticion = seguridad_pb2.PeticionRegistro(
                usuario=request.usuario, 
                password=request.password, 
                rol=request.rol,
                creador=request.creador
            )
            res_auth = cliente_auth.RegistrarUsuario(peticion)
            return orquestador_pb2.RespuestaRegistroOrquestador(exito=res_auth.exito, mensaje=res_auth.mensaje)

    def EnviarComando(self, request, context):
        with grpc.insecure_channel('localhost:50053') as canal_auth:
            cliente_auth = seguridad_pb2_grpc.ServicioSeguridadStub(canal_auth)
            res_validar = cliente_auth.ValidarToken(seguridad_pb2.PeticionValidacion(token=request.token))
            if not res_validar.valido:
                return orquestador_pb2.RespuestaComandoOrquestador(exito=False, mensaje="[ERROR] Token invalido o expirado.", resultado="")
            
            usuario_actual = res_validar.usuario
            rol_actual = res_validar.rol

        if request.tipo == "SQL":
            return self._ejecutar_parser_sql(request.comando, request.token, usuario_actual, rol_actual)
        else:
            return self._ejecutar_parser_json(request.comando, request.token, usuario_actual, rol_actual)

    def _procesar_admin(self, token, accion, base_datos, tabla, usuario):
        with grpc.insecure_channel('localhost:50052') as canal_meta:
            cliente_meta = metadatos_pb2_grpc.ServicioAdministracionStub(canal_meta)
            peticion = metadatos_pb2.PeticionAdmin(accion=accion, base_datos=base_datos, tabla=tabla, usuario=usuario)
            res_meta = cliente_meta.GestionarCatalogo(peticion)
            if res_meta.exito:
                mandar_log_asincrono(f"Usuario {usuario} ejecuto {accion} en {base_datos}")
            return orquestador_pb2.RespuestaComandoOrquestador(exito=res_meta.exito, mensaje=res_meta.mensaje, resultado=res_meta.datos if accion == "listar_dbs" else "")

    def _procesar_crud(self, token, base_datos, tabla, accion, datos_json, usuario, rol):
        if rol == "usuario_lectura" and accion not in ["buscar", "join"]:
            return orquestador_pb2.RespuestaComandoOrquestador(exito=False, mensaje="[ERROR] Tu rol de lectura no permite modificaciones.", resultado="")

        with grpc.insecure_channel('localhost:50052') as canal_meta:
            cliente_meta = metadatos_pb2_grpc.ServicioAdministracionStub(canal_meta)
            res_meta = cliente_meta.GestionarCatalogo(metadatos_pb2.PeticionAdmin(accion="listar_dbs"))
            catalogo = json.loads(res_meta.datos)
            
            if base_datos not in catalogo:
                return orquestador_pb2.RespuestaComandoOrquestador(exito=False, mensaje="[ERROR] La base de datos no existe.", resultado="")
                
            propietario = catalogo[base_datos]["propietario"]
            if propietario != usuario and rol != "administrador":
                return orquestador_pb2.RespuestaComandoOrquestador(exito=False, mensaje=f"[ERROR] Acceso denegado. Propiedad de {propietario}.", resultado="")

            if accion not in ["crear_db"] and tabla not in catalogo[base_datos]["tablas"]:
                return orquestador_pb2.RespuestaComandoOrquestador(exito=False, mensaje="[ERROR] La tabla origen no existe.", resultado="")

            if accion == "join":
                params_j = json.loads(datos_json)
                t2_completa = params_j.get("tabla2", "")
                if "_" in t2_completa:
                    db2_chk, t2_chk = t2_completa.split("_", 1)
                    if db2_chk not in catalogo or t2_chk not in catalogo[db2_chk]["tablas"]:
                        return orquestador_pb2.RespuestaComandoOrquestador(exito=False, mensaje="[ERROR] La segunda tabla especificada en el JOIN no existe.", resultado="")

        with grpc.insecure_channel('localhost:50051') as canal_storage:
            cliente_storage = base_datos_pb2_grpc.ServicioAlmacenamientoStub(canal_storage)
            peticion_db = base_datos_pb2.PeticionConsulta(tabla=f"{base_datos}_{tabla}", accion=accion, datos_json=datos_json)
            res_db = cliente_storage.EjecutarConsulta(peticion_db)
            if res_db.exito:
                mandar_log_asincrono(f"Usuario {usuario} ejecuto {accion} en {base_datos}.{tabla}")
            return orquestador_pb2.RespuestaComandoOrquestador(exito=res_db.exito, mensaje=res_db.mensaje, resultado=res_db.resultado)

    def _procesar_agregacion(self, token, base_datos, tabla, operacion, campo, usuario, rol):
        with grpc.insecure_channel('localhost:50052') as canal_meta:
            cliente_meta = metadatos_pb2_grpc.ServicioAdministracionStub(canal_meta)
            res_meta = cliente_meta.GestionarCatalogo(metadatos_pb2.PeticionAdmin(accion="listar_dbs"))
            catalogo = json.loads(res_meta.datos)
            
            if base_datos not in catalogo or tabla not in catalogo[base_datos]["tablas"]:
                return orquestador_pb2.RespuestaComandoOrquestador(exito=False, mensaje="[ERROR] Estructura no valida.", resultado="")
                
            propietario = catalogo[base_datos]["propietario"]
            if propietario != usuario and rol != "administrador":
                return orquestador_pb2.RespuestaComandoOrquestador(exito=False, mensaje="[ERROR] No tienes acceso a esta base de datos.", resultado="")

        with grpc.insecure_channel('localhost:50054') as canal_mpi:
            cliente_mpi = agregacion_pb2_grpc.ServicioAgregacionStub(canal_mpi)
            peticion_mpi = agregacion_pb2.PeticionAgregacion(operacion=operacion.upper(), db_tabla=f"{base_datos}_{tabla}", campo=campo)
            res_mpi = cliente_mpi.Calcular(peticion_mpi)
            if res_mpi.exito:
                mandar_log_asincrono(f"Calculo distribuido {operacion} en {base_datos}.{tabla}")
            return orquestador_pb2.RespuestaComandoOrquestador(exito=res_mpi.exito, mensaje=res_mpi.mensaje, resultado=res_mpi.resultado)

    def _ejecutar_parser_sql(self, comando, token, usuario, rol):
        match_show_dbs = re.match(r"SHOW DATABASES", comando, re.IGNORECASE)
        if match_show_dbs:
            return self._procesar_admin(token, "listar_dbs", "", "", usuario)

        match_drop_db = re.match(r"DROP DATABASE (\w+)", comando, re.IGNORECASE)
        if match_drop_db:
            return self._procesar_admin(token, "eliminar_db", match_drop_db.group(1), "", usuario)

        match_drop_table = re.match(r"DROP TABLE (\w+)\.(\w+)", comando, re.IGNORECASE)
        if match_drop_table:
            return self._procesar_admin(token, "eliminar_tabla", match_drop_table.group(1), match_drop_table.group(2), usuario)

        match_create_db = re.match(r"CREATE DATABASE (\w+)", comando, re.IGNORECASE)
        if match_create_db:
            return self._procesar_admin(token, "crear_db", match_create_db.group(1), "", usuario)

        match_create_table = re.match(r"CREATE TABLE (\w+)\.(\w+)", comando, re.IGNORECASE)
        if match_create_table:
            return self._procesar_admin(token, "crear_tabla", match_create_table.group(1), match_create_table.group(2), usuario)

        match_join = re.match(r"SELECT \* FROM (\w+)\.(\w+) JOIN (\w+)\.(\w+) ON (\w+)", comando, re.IGNORECASE)
        if match_join:
            db1, t1, db2, t2, campo = match_join.groups()
            js = json.dumps({"tabla2": f"{db2}_{t2}", "on": campo})
            return self._procesar_crud(token, db1, t1, "join", js, usuario, rol)

        match_update = re.match(r"UPDATE (\w+)\.(\w+) SET (.*) WHERE (.*)", comando, re.IGNORECASE)
        if match_update:
            js = f'{{"filtro": {match_update.group(4)}, "valores": {match_update.group(3)}}}'
            return self._procesar_crud(token, match_update.group(1), match_update.group(2), "actualizar", js, usuario, rol)

        match_agregacion = re.match(r"SELECT (COUNT|SUM|AVG)\((\w+)\) FROM (\w+)\.(\w+)", comando, re.IGNORECASE)
        if match_agregacion:
            return self._procesar_agregacion(token, match_agregacion.group(3), match_agregacion.group(4), match_agregacion.group(1), match_agregacion.group(2), usuario, rol)

        match_insert = re.match(r"INSERT INTO (\w+)\.(\w+) VALUES \((.*)\)", comando, re.IGNORECASE)
        if match_insert:
            return self._procesar_crud(token, match_insert.group(1), match_insert.group(2), "insertar", match_insert.group(3), usuario, rol)

        match_select = re.match(r"SELECT \* FROM (\w+)\.(\w+)(?: WHERE (.*))?", comando, re.IGNORECASE)
        if match_select:
            filtro = match_select.group(3) if match_select.group(3) else "{}"
            return self._procesar_crud(token, match_select.group(1), match_select.group(2), "buscar", filtro, usuario, rol)

        match_delete = re.match(r"DELETE FROM (\w+)\.(\w+) WHERE (.*)", comando, re.IGNORECASE)
        if match_delete:
            return self._procesar_crud(token, match_delete.group(1), match_delete.group(2), "eliminar", match_delete.group(3), usuario, rol)

        return orquestador_pb2.RespuestaComandoOrquestador(exito=False, mensaje="[ERROR] Sintaxis SQL no reconocida.", resultado="")

    def _ejecutar_parser_json(self, comando, token, usuario, rol):
        try:
            obj = json.loads(comando)
            accion = obj["accion"].upper()
            if accion in ["COUNT", "SUM", "AVG"]:
                return self._procesar_agregacion(token, obj["db"], obj["tabla"], accion, obj.get("campo", ""), usuario, rol)
            elif accion in ["CREAR_DB", "CREAR_TABLA"]:
                return self._procesar_admin(token, accion.lower(), obj["db"], obj.get("tabla", ""), usuario)
            else:
                return self._procesar_crud(token, obj["db"], obj["tabla"], obj["accion"], json.dumps(obj.get("datos", {})), usuario, rol)
        except Exception as e:
            return orquestador_pb2.RespuestaComandoOrquestador(exito=False, mensaje=f"[ERROR] JSON invalido: {str(e)}", resultado="")

def iniciar():
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    orquestador_pb2_grpc.add_ServicioOrquestadorServicer_to_server(OrquestadorServidor(), servidor)
    servidor.add_insecure_port('[::]:50050')
    print("[INFO] Orquestador activo como servidor en el puerto 50050...")
    servidor.start()
    servidor.wait_for_termination()

if __name__ == '__main__':
    iniciar()