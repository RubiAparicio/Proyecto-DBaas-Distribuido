import sys
import os
import grpc
import subprocess
from concurrent import futures

ruta_protos = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'protos'))
sys.path.append(ruta_protos)

import agregacion_pb2, agregacion_pb2_grpc

class ServicioAgregacion(agregacion_pb2_grpc.ServicioAgregacionServicer):
    def Calcular(self, request, context):
        print(f"\nPetición de {request.operacion} recibida para la tabla {request.db_tabla}.")
        
        script_mpi = os.path.join(os.path.dirname(__file__), 'worker_mpi.py')
        
        # Ejecutamos el comando de consola: mpiexec -n 4 python worker_mpi.py operacion tabla campo
        # -n 4 significa que usaremos 4 procesos paralelos
        comando = ["mpiexec", "-n", "4", "python", script_mpi, request.operacion, request.db_tabla, request.campo]
        
        try:
            resultado_consola = subprocess.run(comando, capture_output=True, text=True, check=True)
            # Limpiamos el texto que nos imprimió el script de MPI
            valor_final = resultado_consola.stdout.strip()
            
            return agregacion_pb2.RespuestaAgregacion(
                exito=True,
                resultado=valor_final,
                mensaje=f"Cálculo {request.operacion} completado con MPI."
            )
        except subprocess.CalledProcessError as e:
            return agregacion_pb2.RespuestaAgregacion(
                exito=False, resultado="", mensaje=f"Error en MPI: {e.stderr}"
            )

def iniciar_servidor():
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    agregacion_pb2_grpc.add_ServicioAgregacionServicer_to_server(ServicioAgregacion(), servidor)
    puerto = '50054'
    servidor.add_insecure_port(f'[::]:{puerto}')
    print(f"Servidor de Agregación (MPI) listo en el puerto {puerto}...")
    servidor.start()
    servidor.wait_for_termination()

if __name__ == '__main__':
    iniciar_servidor()