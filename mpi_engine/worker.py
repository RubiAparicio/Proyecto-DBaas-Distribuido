# mpi_engine/worker.py
import pika
import json
import subprocess
import sys

def procesar_mensaje(ch, method, properties, body):
    mensaje = json.loads(body)
    db = mensaje['db_name']
    tabla = mensaje['table_name']
    op = mensaje['operation']
    
    print(f"\n[x] Tarea de agregación recibida: {op} en {db}.{tabla}")
    print("[x] Encendiendo Clúster MPI con 4 nodos...")
    
    # Aquí es donde ocurre la magia: Le decimos a la consola que ejecute mpiexec
    # -n 4 significa que levantará 4 procesos paralelos
    comando = ["mpiexec", "-n", "4", "python", "mpi_engine/mpi_task.py", db, tabla, op]
    
    try:
        # Ejecutamos el comando y capturamos lo que imprima el Maestro
        resultado = subprocess.run(comando, capture_output=True, text=True)
        
        print("\n=== SALIDA DEL CLÚSTER MPI ===")
        print(resultado.stdout)
        if resultado.stderr:
            print("Errores MPI:", resultado.stderr)
        print("==============================\n")
        
    except Exception as e:
        print(f"Error al ejecutar MPI: {e}")

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='aggregation_tasks')

    channel.basic_consume(queue='aggregation_tasks', on_message_callback=procesar_mensaje, auto_ack=True)

    print(' [*] Motor de Agregación esperando mensajes en RabbitMQ. Para salir presiona CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    main()