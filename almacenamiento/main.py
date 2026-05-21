import sys
import os
import json
import grpc
from concurrent import futures

ruta_protos = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'protos'))
sys.path.append(ruta_protos)

import base_datos_pb2
import base_datos_pb2_grpc

class ServicioAlmacenamiento(base_datos_pb2_grpc.ServicioAlmacenamientoServicer):
    
    def EjecutarConsulta(self, request, context):
        print(f"\n[INFO] Orden recibida: '{request.accion}' en la tabla '{request.tabla}'.")
        
        carpeta_datos = os.path.join(os.path.dirname(__file__), 'datos')
        os.makedirs(carpeta_datos, exist_ok=True)
        ruta_archivo = os.path.join(carpeta_datos, f"{request.tabla}.json")
        
        datos_actuales = []
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
                datos_actuales = json.load(archivo)
        
        try:
            # --- ACCION: INSERTAR ---
            if request.accion == "insertar":
                nuevo_dato = json.loads(request.datos_json)
                datos_actuales.append(nuevo_dato)
                
                with open(ruta_archivo, 'w', encoding='utf-8') as archivo:
                    json.dump(datos_actuales, archivo, indent=4)
                    
                return base_datos_pb2.RespuestaConsulta(
                    exito=True,
                    mensaje=f"Dato guardado correctamente en {request.tabla}.json",
                    resultado=""
                )
            
            # --- ACCION: BUSCAR ---
            elif request.accion == "buscar":
                filtro = json.loads(request.datos_json)
                
                if not filtro:
                    resultado_filtrado = datos_actuales
                else:
                    resultado_filtrado = []
                    for registro in datos_actuales:
                        coincide = True
                        for llave, valor in filtro.items():
                            if registro.get(llave) != valor:
                                coincide = False
                                break
                        if coincide:
                            resultado_filtrado.append(registro)
                
                return base_datos_pb2.RespuestaConsulta(
                    exito=True,
                    mensaje=f"Busqueda realizada. Se encontraron {len(resultado_filtrado)} registros.",
                    resultado=json.dumps(resultado_filtrado)
                )
            
            # --- ACCION: ACTUALIZAR ---
            elif request.accion == "actualizar":
                datos_recibidos = json.loads(request.datos_json)
                filtro = datos_recibidos.get("filtro", {})
                nuevos_valores = datos_recibidos.get("valores", {})
                
                if not filtro:
                    return base_datos_pb2.RespuestaConsulta(
                        exito=False, mensaje="Por seguridad, necesitas un filtro para actualizar.", resultado=""
                    )
                
                actualizados = 0
                for registro in datos_actuales:
                    coincide = True
                    for llave, valor in filtro.items():
                        if registro.get(llave) != valor:
                            coincide = False
                            break
                    if coincide:
                        for k, v in nuevos_valores.items():
                            registro[k] = v
                        actualizados += 1
                
                with open(ruta_archivo, 'w', encoding='utf-8') as archivo:
                    json.dump(datos_actuales, archivo, indent=4)
                    
                return base_datos_pb2.RespuestaConsulta(
                    exito=True,
                    mensaje=f"Actualizacion completada. Se modificaron {actualizados} registros.",
                    resultado=""
                )
            
            # --- ACCION: ELIMINAR ---
            elif request.accion == "eliminar":
                filtro = json.loads(request.datos_json)
                
                if not filtro:
                    return base_datos_pb2.RespuestaConsulta(
                        exito=False,
                        mensaje="Por seguridad, no puedes eliminar sin un filtro.",
                        resultado=""
                    )
                
                nuevos_datos = []
                eliminados = 0
                for registro in datos_actuales:
                    coincide = True
                    for llave, valor in filtro.items():
                        if registro.get(llave) != valor:
                            coincide = False
                            break
                    if coincide:
                        eliminados += 1
                    else:
                        nuevos_datos.append(registro)
                
                with open(ruta_archivo, 'w', encoding='utf-8') as archivo:
                    json.dump(nuevos_datos, archivo, indent=4)
                    
                return base_datos_pb2.RespuestaConsulta(
                    exito=True,
                    mensaje=f"Eliminacion completada. Se borraron {eliminados} registros.",
                    resultado=""
                )

            # --- ACCION: INNER JOIN ---
            elif request.accion == "join":
                params = json.loads(request.datos_json)
                tabla2_completa = params.get("tabla2")
                campo_on = params.get("on")
                
                ruta_archivo2 = os.path.join(carpeta_datos, f"{tabla2_completa}.json")
                datos_tabla2 = []
                if os.path.exists(ruta_archivo2):
                    with open(ruta_archivo2, 'r', encoding='utf-8') as archivo2:
                        datos_tabla2 = json.load(archivo2)
                
                resultado_join = []
                for reg1 in datos_actuales:
                    if campo_on in reg1:
                        val_comun = reg1[campo_on]
                        for reg2 in datos_tabla2:
                            if campo_on in reg2 and reg2[campo_on] == val_comun:
                                combinado = reg1.copy()
                                for k, v in reg2.items():
                                    if k not in combinado:
                                        combinado[k] = v
                                    elif k == campo_on:
                                        continue
                                    else:
                                        combinado[f"t2_{k}"] = v
                                resultado_join.append(combinado)
                
                return base_datos_pb2.RespuestaConsulta(
                    exito=True,
                    mensaje=f"Inner Join realizado de forma exitosa. {len(resultado_join)} filas cruzadas.",
                    resultado=json.dumps(resultado_join)
                )
                
            else:
                return base_datos_pb2.RespuestaConsulta(
                    exito=False,
                    mensaje=f"Accion '{request.accion}' no reconocida.",
                    resultado=""
                )
                
        except Exception as e:
            return base_datos_pb2.RespuestaConsulta(
                exito=False,
                mensaje=f"Error en la operacion: {str(e)}",
                resultado=""
            )

def iniciar_servidor():
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    base_datos_pb2_grpc.add_ServicioAlmacenamientoServicer_to_server(ServicioAlmacenamiento(), servidor)
    puerto = '50051'
    servidor.add_insecure_port(f'[::]:{puerto}')
    print(f"[INFO] Servidor de almacenamiento listo en el puerto {puerto}...")
    servidor.start()
    servidor.wait_for_termination()

if __name__ == '__main__':
    iniciar_servidor()