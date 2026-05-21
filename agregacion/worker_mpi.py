from mpi4py import MPI
import sys
import json
import os

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # Recibimos los argumentos desde la terminal
    operacion = sys.argv[1]
    tabla = sys.argv[2]
    campo = sys.argv[3]

    datos = None

    # El NODO MASTER (rank 0) lee el archivo
    if rank == 0:
        ruta_archivo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'almacenamiento', 'datos', f"{tabla}.json"))
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos_completos = json.load(f)
                
                # Extraemos solo los números que nos interesan
                if operacion in ["SUM", "AVG"]:
                    datos = [float(item.get(campo, 0)) for item in datos_completos if campo in item]
                elif operacion == "COUNT":
                    datos = [1 for item in datos_completos] # Un 1 por cada registro
        else:
            datos = []

        # Dividimos los datos en partes iguales para los workers
        chunks = [[] for _ in range(size)]
        for i, valor in enumerate(datos):
            chunks[i % size].append(valor)
    else:
        chunks = None

    # SCATTER: El Master reparte los pedazos a los workers
    mi_pedazo = comm.scatter(chunks, root=0)

    # TRABAJO LOCAL: Cada worker suma su pedazo
    suma_local = sum(mi_pedazo)
    elementos_locales = len(mi_pedazo)

    # GATHER: El Master junta los subtotales de todos
    sumas_totales = comm.gather(suma_local, root=0)
    conteos_totales = comm.gather(elementos_locales, root=0)

    # El Master calcula el resultado final y lo imprime (para que el servidor gRPC lo lea)
    if rank == 0:
        suma_final = sum(sumas_totales)
        total_elementos = sum(conteos_totales)
        
        if operacion == "SUM" or operacion == "COUNT":
            print(suma_final)
        elif operacion == "AVG":
            promedio = suma_final / total_elementos if total_elementos > 0 else 0
            print(promedio)

if __name__ == '__main__':
    main()