import sys
import os
import json
import grpc
from concurrent import futures

ruta_protos = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'protos'))
sys.path.append(ruta_protos)

import metadatos_pb2
import metadatos_pb2_grpc

class ServicioAdministracion(metadatos_pb2_grpc.ServicioAdministracionServicer):
    def __init__(self):
        self.archivo_catalogo = os.path.join(os.path.dirname(__file__), 'catalogo.json')
        if not os.path.exists(self.archivo_catalogo):
            with open(self.archivo_catalogo, 'w', encoding='utf-8') as archivo:
                json.dump({}, archivo)

    def _leer_catalogo(self):
        with open(self.archivo_catalogo, 'r', encoding='utf-8') as archivo:
            return json.load(archivo)

    def _guardar_catalogo(self, datos):
        with open(self.archivo_catalogo, 'w', encoding='utf-8') as archivo:
            json.dump(datos, archivo, indent=4)

    def GestionarCatalogo(self, request, context):
        print(f"\n[INFO] Peticion administrativa recibida: '{request.accion}'")
        catalogo = self._leer_catalogo()

        try:
            if request.accion == "crear_db":
                if request.base_datos in catalogo:
                    return metadatos_pb2.RespuestaAdmin(exito=False, mensaje="La base de datos ya existe.", datos="")
                
                catalogo[request.base_datos] = {
                    "propietario": request.usuario, 
                    "tablas": []
                }
                self._guardar_catalogo(catalogo)
                return metadatos_pb2.RespuestaAdmin(exito=True, mensaje=f"Base de datos creada.", datos="")

            elif request.accion == "crear_tabla":
                if request.base_datos not in catalogo:
                    return metadatos_pb2.RespuestaAdmin(exito=False, mensaje="La base de datos no existe.", datos="")
                
                if request.tabla in catalogo[request.base_datos]["tablas"]:
                    return metadatos_pb2.RespuestaAdmin(exito=False, mensaje="La tabla ya existe.", datos="")
                
                catalogo[request.base_datos]["tablas"].append(request.tabla)
                self._guardar_catalogo(catalogo)
                return metadatos_pb2.RespuestaAdmin(exito=True, mensaje=f"Tabla creada.", datos="")

            elif request.accion == "listar_dbs":
                return metadatos_pb2.RespuestaAdmin(exito=True, mensaje="Catalogo recuperado.", datos=json.dumps(catalogo))

            elif request.accion == "eliminar_db":
                if request.base_datos not in catalogo:
                    return metadatos_pb2.RespuestaAdmin(exito=False, mensaje="La base de datos no existe.", datos="")
                
                del catalogo[request.base_datos]
                self._guardar_catalogo(catalogo)
                return metadatos_pb2.RespuestaAdmin(exito=True, mensaje="Base de datos eliminada.", datos="")

            elif request.accion == "eliminar_tabla":
                if request.base_datos not in catalogo or request.tabla not in catalogo[request.base_datos]["tablas"]:
                    return metadatos_pb2.RespuestaAdmin(exito=False, mensaje="La tabla o base de datos no existen.", datos="")
                
                catalogo[request.base_datos]["tablas"].remove(request.tabla)
                self._guardar_catalogo(catalogo)
                return metadatos_pb2.RespuestaAdmin(exito=True, mensaje="Tabla eliminada del catalogo.", datos="")

            else:
                return metadatos_pb2.RespuestaAdmin(exito=False, mensaje=f"Accion no reconocida.", datos="")

        except Exception as e:
            return metadatos_pb2.RespuestaAdmin(exito=False, mensaje=f"Error interno: {str(e)}", datos="")

def iniciar_servidor():
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    metadatos_pb2_grpc.add_ServicioAdministracionServicer_to_server(ServicioAdministracion(), servidor)
    puerto = '50052'
    servidor.add_insecure_port(f'[::]:{puerto}')
    print(f"[INFO] Servidor de Metadatos listo en el puerto {puerto}...")
    servidor.start()
    servidor.wait_for_termination()

if __name__ == '__main__':
    iniciar_servidor()