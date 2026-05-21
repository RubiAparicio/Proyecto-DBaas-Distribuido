import sys
import os
import grpc
import jwt
import json
import datetime
from concurrent import futures

ruta_protos = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'protos'))
sys.path.append(ruta_protos)

import seguridad_pb2
import seguridad_pb2_grpc

CLAVE_SECRETA = "mi_clave_super_secreta_para_el_proyecto"

class ServicioSeguridad(seguridad_pb2_grpc.ServicioSeguridadServicer):
    def __init__(self):
        self.archivo_usuarios = os.path.join(os.path.dirname(__file__), 'usuarios.json')
        if not os.path.exists(self.archivo_usuarios):
            # Por defecto, eduardo es admin y es su propio jefe (creador)
            admin_inicial = {"eduardo": {"password": "123", "rol": "administrador", "creador": "eduardo"}}
            with open(self.archivo_usuarios, 'w', encoding='utf-8') as archivo:
                json.dump(admin_inicial, archivo, indent=4)

    def _leer_usuarios(self):
        with open(self.archivo_usuarios, 'r', encoding='utf-8') as archivo:
            return json.load(archivo)

    def RegistrarUsuario(self, request, context):
        print(f"[INFO] Peticion de registro para el usuario: '{request.usuario}' (Creado por: {request.creador})")
        usuarios_db = self._leer_usuarios()
        
        if request.usuario in usuarios_db:
            return seguridad_pb2.RespuestaRegistro(exito=False, mensaje="El usuario ya existe.")
            
        # NUEVO: Guardamos quien lo creo. Si el creador esta vacio, el mismo es su creador (es admin principal).
        jefe = request.creador if request.creador else request.usuario
        
        usuarios_db[request.usuario] = {
            "password": request.password, 
            "rol": request.rol,
            "creador": jefe
        }
        
        with open(self.archivo_usuarios, 'w', encoding='utf-8') as archivo:
            json.dump(usuarios_db, archivo, indent=4)
            
        return seguridad_pb2.RespuestaRegistro(exito=True, mensaje="Usuario registrado exitosamente.")

    def IniciarSesion(self, request, context):
        print(f"[INFO] Intento de login del usuario: '{request.usuario}'")
        usuarios_db = self._leer_usuarios()
        usuario_info = usuarios_db.get(request.usuario)
        
        if usuario_info and usuario_info["password"] == request.password:
            payload = {
                "usuario": request.usuario,
                "rol": usuario_info["rol"],
                "jefe": usuario_info["creador"], # Metemos al jefe en el token
                "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
            }
            token = jwt.encode(payload, CLAVE_SECRETA, algorithm="HS256")
            return seguridad_pb2.RespuestaToken(exito=True, token=token, mensaje="Login exitoso")
        else:
            return seguridad_pb2.RespuestaToken(exito=False, token="", mensaje="Credenciales incorrectas")

    def ValidarToken(self, request, context):
        try:
            payload = jwt.decode(request.token, CLAVE_SECRETA, algorithms=["HS256"])
            # NUEVO: Devolvemos el jefe en el campo usuario si no es admin, para engañar a metadatos y dejarlo pasar
            usuario_efectivo = payload["usuario"] if payload["rol"] == "administrador" else payload["jefe"]
            
            return seguridad_pb2.RespuestaValidacion(valido=True, rol=payload["rol"], usuario=usuario_efectivo)
        except jwt.ExpiredSignatureError:
            return seguridad_pb2.RespuestaValidacion(valido=False, rol="", usuario="Token expirado")
        except jwt.InvalidTokenError:
            return seguridad_pb2.RespuestaValidacion(valido=False, rol="", usuario="Token invalido")

def iniciar_servidor():
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    seguridad_pb2_grpc.add_ServicioSeguridadServicer_to_server(ServicioSeguridad(), servidor)
    puerto = '50053'
    servidor.add_insecure_port(f'[::]:{puerto}')
    print(f"[INFO] Servidor de Seguridad listo en el puerto {puerto}...")
    servidor.start()
    servidor.wait_for_termination()

if __name__ == '__main__':
    iniciar_servidor()