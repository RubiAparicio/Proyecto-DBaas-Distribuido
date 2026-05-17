# mpi_engine/mpi_task.py
from mpi4py import MPI
import sys
import json
import os

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank() 
    size = comm.Get_size() 

    if len(sys.argv) < 4:
        if rank == 0: print("Error: Faltan argumentos.")
        return

    db_name = sys.argv[1]
    table_name = sys.argv[2]
    operation = sys.argv[3].upper()
    
    # Columnas objetivo para demostración
    col_numerica = "edad" 
    col_texto = "nombre"

    chunks = None
    table2_data = None

    # --- EL MAESTRO LEE Y PREPARA LOS DATOS ---
    if rank == 0:
        # Si es un JOIN, asumimos que nos pasaron dos tablas separadas por coma (ej: "usuarios,pedidos")
        if operation == "JOIN":
            tablas = table_name.split(",")
            if len(tablas) != 2:
                print("Error: Para JOIN debes enviar dos tablas (ej. tabla1,tabla2)")
                comm.Abort()
                
            file1 = os.path.join("./data", db_name, f"{tablas[0]}.json")
            file2 = os.path.join("./data", db_name, f"{tablas[1]}.json")
            
            with open(file1, 'r') as f1, open(file2, 'r') as f2:
                full_data = json.load(f1)
                table2_data = json.load(f2) # La tabla 2 se la pasaremos completa a todos
        else:
            file_path = os.path.join("./data", db_name, f"{table_name}.json")
            with open(file_path, 'r') as f:
                full_data = json.load(f)

        print(f"[Nodo 0] Repartiendo {len(full_data)} registros base entre {size} nodos...")
        
        # Dividimos los datos de la tabla principal
        chunk_size = len(full_data) // size
        chunks = [full_data[i * chunk_size:(i + 1) * chunk_size] for i in range(size)]
        for i in range(len(full_data) % size):
            chunks[i].append(full_data[size * chunk_size + i])

    # --- SCATTER Y BROADCAST ---
    # Repartimos la tabla principal a pedazos
    data_chunk = comm.scatter(chunks, root=0)
    
    # Si es JOIN, enviamos una copia de la Tabla 2 COMPLETA a todos los nodos
    if operation == "JOIN":
        table2_data = comm.bcast(table2_data, root=0)

    # --- PROCESAMIENTO PARALELO (MAP) ---
    resultado_local = None
    
    if operation == "COUNT":
        resultado_local = len(data_chunk)
        print(f"[Nodo {rank}] Conté {resultado_local} registros.")
        
    elif operation == "SUM":
        resultado_local = sum(item.get(col_numerica, 0) for item in data_chunk if isinstance(item.get(col_numerica), (int, float)))
        print(f"[Nodo {rank}] Suma local: {resultado_local}.")
        
    elif operation == "AVG":
        suma_local = sum(item.get(col_numerica, 0) for item in data_chunk if isinstance(item.get(col_numerica), (int, float)))
        conteo_local = len([item for item in data_chunk if isinstance(item.get(col_numerica), (int, float))])
        resultado_local = (suma_local, conteo_local)
        print(f"[Nodo {rank}] Promedio local procesado.")
        
    elif operation == "DISTINCT":
        # Extraemos valores únicos usando un set de Python
        resultado_local = set(item.get(col_texto) for item in data_chunk if col_texto in item)
        print(f"[Nodo {rank}] Encontré {len(resultado_local)} nombres únicos.")
        
    elif operation == "JOIN":
        # JOIN simple anidado (O(N*M)) simulando un cruce por la llave "nombre"
        join_local = []
        for row1 in data_chunk:
            for row2 in table2_data:
                if row1.get("nombre") == row2.get("nombre"):
                    combinado = {**row1, **row2} # Fusionamos ambos diccionarios
                    join_local.append(combinado)
        resultado_local = join_local
        print(f"[Nodo {rank}] Realicé {len(join_local)} cruces exitosos.")

    # --- GATHER (REDUCIR) ---
    resultados_globales = comm.gather(resultado_local, root=0)

    # --- RESULTADO FINAL EN EL MAESTRO ---
    if rank == 0:
        print("-" * 40)
        if operation in ["COUNT", "SUM"]:
            final = sum(resultados_globales)
            print(f"RESULTADO FINAL DE {operation}: {final}")
            
        elif operation == "AVG":
            suma_total = sum(r[0] for r in resultados_globales)
            conteo_total = sum(r[1] for r in resultados_globales)
            promedio = suma_total / conteo_total if conteo_total > 0 else 0
            print(f"RESULTADO FINAL DE AVG: {promedio}")
            
        elif operation == "DISTINCT":
            # Unimos todos los sets
            set_final = set()
            for s in resultados_globales:
                set_final = set_final.union(s)
            print(f"RESULTADO FINAL DE DISTINCT: {list(set_final)}")
            
        elif operation == "JOIN":
            # Juntamos todas las listas de cruces
            lista_final = []
            for lista in resultados_globales:
                lista_final.extend(lista)
            print(f"RESULTADO FINAL DE JOIN: Se generaron {len(lista_final)} registros combinados.")
            # print(json.dumps(lista_final, indent=2)) # Opcional: imprimir los datos unidos
        print("-" * 40)

if __name__ == "__main__":
    main()