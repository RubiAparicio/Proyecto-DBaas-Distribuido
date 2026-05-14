# Proyecto Final - Programación Distribuida Aplicada

## Servicio distribuido DBaaS simplificado basado en microservicios

### Integrantes:
- Aparicio Rosas Rubi - 202213444
- Carmona Torreblanca Eduardo Isaí - 202237115

## Descripción

Este proyecto consiste en el desarrollo de una plataforma distribuida de almacenamiento y consulta de datos como servicio (DBaaS) basada en una arquitectura de microservicios.

El sistema permitirá a los usuarios administrar bases de datos lógicas, tablas o colecciones, realizar operaciones CRUD y ejecutar consultas de agregación sin necesidad de conocer un Sistema Gestor de Bases de Datos (SGBD).

La plataforma implementará:

- Comunicación síncrona mediante gRPC.
- Comunicación asíncrona mediante RabbitMQ.
- Procesamiento distribuido utilizando MPI para operaciones de agregación.
- Seguridad mediante autenticación JWT y control de roles.
- Interfaces SQL-like y NoSQL-like basadas en JSON.

---

# Objetivos

## Objetivo General

Desarrollar un sistema distribuido tipo DBaaS basado en microservicios que permita administrar y consultar datos de manera segura y transparente.

## Objetivos Específicos

- Implementar microservicios independientes.
- Implementar autenticación y autorización mediante JWT.
- Desarrollar operaciones CRUD distribuidas.
- Implementar consultas de agregación utilizando MPI.
- Integrar RabbitMQ para tareas asíncronas.
- Implementar interfaces SQL-like y NoSQL-like.

---

# Arquitectura del Sistema

El sistema estará compuesto por varios microservicios:

## Microservicios principales

- Servicio de autenticación.
- Servicio de almacenamiento.
- Servicio de consultas.
- Servicio de agregación.
- Servicio de mensajería asíncrona.

## Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python | Desarrollo principal |
| gRPC | Comunicación síncrona |
| RabbitMQ | Comunicación asíncrona |
| MPI | Procesamiento distribuido |
| JWT | Autenticación |
| JSON | Interfaz NoSQL-like |
| Docker | Contenedores |
| Git/GitHub | Control de versiones |

---

# Funcionalidades Obligatorias

## Administración

- Crear base de datos.
- Listar bases de datos.
- Eliminar base de datos.
- Crear tabla o colección.
- Listar tablas o colecciones.
- Eliminar tabla o colección.

---

## Seguridad

- Registro local de usuarios.
- Login local.
- Autenticación mediante JWT.
- Roles:
  - Administrador.
  - Usuario de escritura.
  - Usuario de lectura.

---

## CRUD

- Insertar registros.
- Buscar registros.
- Actualizar registros.
- Eliminar registros.

---

## Consultas

- COUNT
- SUM
- AVG
- DISTINCT
- INNER JOIN simple entre dos tablas

---
