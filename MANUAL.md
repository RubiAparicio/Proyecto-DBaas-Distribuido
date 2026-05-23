## Guía de Instalación y Ejecución

### Integrantes:
- Aparicio Rosas Rubi - 202213444
- Carmona Torreblanca Eduardo Isaí - 202237115
- Gutierrez Paz Guadalupe Alondra - 202226959
- Salazar Huerta Guadalupe - 202158692

## Descripción
Este es el manual para desplegar el sistema de base de datos distribuida.

## Objetivo General

Desarrollar un sistema distribuido tipo DBaaS basado en microservicios que permita administrar y consultar datos de manera segura y transparente.

## 1. Requisitos Previos

- En las 5 laptops: Python.
- Solo en la Laptop 4: Microsoft MPI para el cálculo distribuido.
- Solo en la Laptop 5: RabbitMQ Server activos.
- Librerías de Python: En cada laptop, abre la terminal en la carpeta del proyecto y ejecuta:

    `pip install grpcio grpcio-tools pika PyJWT mpi4py`

El sistema estará compuesto por varios microservicios:

---

## 2. Preparación Crítica de la Red

- Conectar las 5 computadoras a la misma red local (Wi-Fi o LAN).
- Apagar el Firewall de Windows Defender en las 5 máquinas (red pública y privada) o configurar los piertos necesarios para permitir el tráfico de gRPC a través de los puertos asignados.

## Mapa de Nodos y Puertos

| Laptop | Rol del Microservicio | Dirección IP Fija | Puerto Asignado |
|---|---|---|---|
| 1 | Orquestador| - | 50056 |
| 2 | Almacenamiento | 172.31.0.249 | 50057 |
| 3 | Seguridad y Metadatos | 172.31.2.172 | 50053 y 50052 |
| 4 | Agregación | 172.31.2.248 | 50054 |
| 5 | Cliente CLI y RABBIT | 172.31.4.1 | 5672 |

---

# Secuencia Estricta de Arranque
Para evitar errores de conexión rechazada (Connection Refused), los servicios deben levantarse respetando la siguiente jerarquía. Navegar a las carpetas correspondientes en cada laptop y ejecutar:

## Fase 1: Servicios de Soporte y Almacenamiento (Laptops 2, 3, 4 y 5)

- Laptop 2: python main.py (dentro de la carpeta almacenamiento)
- Laptop 3: python main.py (en autenticacion) y python main.py (en metadatos) en dos terminales separadas.
- Laptop 4: python main.py (dentro de la carpeta agregacion)
- Laptop 5: Levantar el contenedor de RabbitMQ en Docker (docker run -d -p 5672:5672 rabbitmq) y luego ejecutar python main.py (dentro de la carpeta auditoria).
- Laptop 1: python main.py (dentro de la carpeta orquestador)
- Laptop 5: python cliente.py

---
