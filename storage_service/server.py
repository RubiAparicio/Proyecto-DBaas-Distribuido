import grpc
from concurrent import futures
import time, os, json, sys, shutil

sys.path.append('.')
import storage_pb2
import storage_pb2_grpc

DATA_DIR = "./data"

class StorageService(storage_pb2_grpc.StorageServiceServicer):
    def __init__(self):
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

    # --- ADMINISTRACIÓN ---
    def CreateDatabase(self, request, context):
        db_path = os.path.join(DATA_DIR, request.db_name)
        if os.path.exists(db_path): return storage_pb2.RecordResponse(success=False, message="La BD ya existe.")
        os.makedirs(db_path)
        return storage_pb2.RecordResponse(success=True, message=f"BD '{request.db_name}' creada.")

    def ListDatabases(self, request, context):
        dbs = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
        return storage_pb2.ListRes(success=True, message="OK", items=dbs)

    def DeleteDatabase(self, request, context):
        db_path = os.path.join(DATA_DIR, request.db_name)
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
            return storage_pb2.RecordResponse(success=True, message="BD eliminada.")
        return storage_pb2.RecordResponse(success=False, message="BD no existe.")

    def CreateTable(self, request, context):
        table_path = os.path.join(DATA_DIR, request.db_name, f"{request.table_name}.json")
        if not os.path.exists(os.path.dirname(table_path)): return storage_pb2.RecordResponse(success=False, message="BD no existe.")
        with open(table_path, 'w') as f: json.dump([], f)
        return storage_pb2.RecordResponse(success=True, message="Tabla creada.")

    def ListTables(self, request, context):
        db_path = os.path.join(DATA_DIR, request.db_name)
        if os.path.exists(db_path):
            tables = [f.replace('.json', '') for f in os.listdir(db_path) if f.endswith('.json')]
            return storage_pb2.ListRes(success=True, message="OK", items=tables)
        return storage_pb2.ListRes(success=False, message="BD no existe.", items=[])

    def DeleteTable(self, request, context):
        table_path = os.path.join(DATA_DIR, request.db_name, f"{request.table_name}.json")
        if os.path.exists(table_path):
            os.remove(table_path)
            return storage_pb2.RecordResponse(success=True, message="Tabla eliminada.")
        return storage_pb2.RecordResponse(success=False, message="Tabla no existe.")

    # --- CRUD (Igual que antes) ---
    def InsertRecord(self, request, context):
        table_path = os.path.join(DATA_DIR, request.db_name, f"{request.table_name}.json")
        if not os.path.exists(os.path.dirname(table_path)): return storage_pb2.RecordResponse(success=False, message="BD no existe.")
        new_record = json.loads(request.data_json)
        if not os.path.exists(table_path):
            with open(table_path, 'w') as f: json.dump([], f)
        with open(table_path, 'r') as f: data = json.load(f)
        data.append(new_record)
        with open(table_path, 'w') as f: json.dump(data, f, indent=4)
        return storage_pb2.RecordResponse(success=True, message="Registro insertado.")

    def FindRecords(self, request, context):
        table_path = os.path.join(DATA_DIR, request.db_name, f"{request.table_name}.json")
        if not os.path.exists(table_path): return storage_pb2.SearchResponse(success=False, message="Tabla no existe.", data_json="[]")
        with open(table_path, 'r') as f: data = json.load(f)
        return storage_pb2.SearchResponse(success=True, message="OK", data_json=json.dumps(data))

    def UpdateRecords(self, request, context):
        table_path = os.path.join(DATA_DIR, request.db_name, f"{request.table_name}.json")
        if not os.path.exists(table_path): return storage_pb2.RecordResponse(success=False, message="Tabla no existe.")
        with open(table_path, 'r') as f: data = json.load(f)
        new_data = json.loads(request.new_data_json)
        for row in data:
            if row.get(request.condition_key) == request.condition_value: row.update(new_data)
        with open(table_path, 'w') as f: json.dump(data, f, indent=4)
        return storage_pb2.RecordResponse(success=True, message="Actualizado.")

    def DeleteRecords(self, request, context):
        table_path = os.path.join(DATA_DIR, request.db_name, f"{request.table_name}.json")
        if not os.path.exists(table_path): return storage_pb2.RecordResponse(success=False, message="Tabla no existe.")
        with open(table_path, 'r') as f: data = json.load(f)
        filtrada = [row for row in data if str(row.get(request.condition_key)) != str(request.condition_value)]
        with open(table_path, 'w') as f: json.dump(filtrada, f, indent=4)
        return storage_pb2.RecordResponse(success=True, message="Eliminado.")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    storage_pb2_grpc.add_StorageServiceServicer_to_server(StorageService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("Storage Service en puerto 50052...")
    try:
        while True: time.sleep(86400)
    except KeyboardInterrupt: server.stop(0)

if __name__ == '__main__': serve()