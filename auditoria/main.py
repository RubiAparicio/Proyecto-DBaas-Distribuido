import pika
import os
import datetime

def procesar_mensaje(ch, method, properties, body):
    mensaje = body.decode('utf-8')
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_linea = f"[{fecha}] AUDITORÍA: {mensaje}\n"
    
    # Guardamos el historial en un archivo txt
    ruta_log = os.path.join(os.path.dirname(__file__), 'historial_operaciones.txt')
    with open(ruta_log, 'a', encoding='utf-8') as archivo:
        archivo.write(log_linea)
        
    print(f" [x] Log guardado asíncronamente: {mensaje}")

def iniciar_auditoria():
    print("Iniciando Servicio de Auditoría asíncrono...")
    try:
        # Nos conectamos al servidor local de RabbitMQ
        conexion = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        canal = conexion.channel()
        
        # Declaramos la cola (si no existe, la crea)
        canal.queue_declare(queue='auditoria_dbaas')
        
        print(' [*] Esperando eventos de la base de datos...')
        
        # Le decimos qué función ejecutar cuando llegue un mensaje
        canal.basic_consume(queue='auditoria_dbaas', on_message_callback=procesar_mensaje, auto_ack=True)
        canal.start_consuming()
    except Exception as e:
        print(f"Error de conexión. ¿Está encendido el servicio de RabbitMQ en Windows? Detalles: {e}")

if __name__ == '__main__':
    iniciar_auditoria()