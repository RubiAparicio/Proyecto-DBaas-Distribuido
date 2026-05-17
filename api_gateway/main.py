from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import grpc, sys, json, pika, jwt, re

sys.path.append('./auth_service')
sys.path.append('./storage_service')
import auth_pb2, auth_pb2_grpc, storage_pb2, storage_pb2_grpc

app = FastAPI()
SECRET_KEY = "mi_clave_super_secreta_para_jwt_123"
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try: return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except: raise HTTPException(status_code=401, detail="Token inválido")

def get_real_db(db_name: str, user: dict):
    owner = user["user"] if user["role"] == "admin" else user["creator"]
    return f"{owner}_{db_name}"

class LoginReq(BaseModel): username: str; password: str
class RegReq(BaseModel): username: str; password: str; role: str
class DBReq(BaseModel): db_name: str
class TableReq(BaseModel): db_name: str; table_name: str
class InsertReq(BaseModel): db_name: str; table_name: str; data: dict
class UpdateReq(BaseModel): db_name: str; table_name: str; condition_key: str; condition_value: str; new_data: dict
class DelReq(BaseModel): db_name: str; table_name: str; condition_key: str; condition_value: str
class QueryReq(BaseModel): db_name: str; table_name: str; operation: str
class SQLReq(BaseModel): query: str

@app.post("/login")
def login(req: LoginReq):
    with grpc.insecure_channel('localhost:50051') as ch:
        stub = auth_pb2_grpc.AuthServiceStub(ch)
        res = stub.Login(auth_pb2.LoginRequest(username=req.username, password=req.password))
        if res.success: return {"token": res.token}
        raise HTTPException(status_code=401, detail=res.message)

# NUEVO: Registro Público (Afuera del candado)
@app.post("/register_public")
def register_public(req: LoginReq):
    with grpc.insecure_channel('localhost:50051') as ch:
        stub = auth_pb2_grpc.AuthServiceStub(ch)
        # Se le asigna rol admin y es su propio creador
        res = stub.Register(auth_pb2.RegisterRequest(username=req.username, password=req.password, role="admin", creator=req.username))
        if res.success: return {"message": res.message}
        raise HTTPException(status_code=400, detail=res.message)

# Registro Interno (Para que el admin cree a sus empleados)
@app.post("/register")
def register(req: RegReq, user: dict = Depends(get_current_user)):
    if user.get("role") != "admin": raise HTTPException(status_code=403, detail="Solo admins crean usuarios")
    with grpc.insecure_channel('localhost:50051') as ch:
        stub = auth_pb2_grpc.AuthServiceStub(ch)
        res = stub.Register(auth_pb2.RegisterRequest(username=req.username, password=req.password, role=req.role, creator=user["user"]))
        if res.success: return {"message": res.message}
        raise HTTPException(status_code=400, detail=res.message)

@app.post("/admin/{action}")
def admin_ops(action: str, req: TableReq, user: dict = Depends(get_current_user)):
    if user.get("role") != "admin": raise HTTPException(status_code=403, detail="Solo admins")
    real_db = get_real_db(req.db_name, user) if req.db_name else ""
    with grpc.insecure_channel('localhost:50052') as ch:
        stub = storage_pb2_grpc.StorageServiceStub(ch)
        if action == "create_db": res = stub.CreateDatabase(storage_pb2.DbReq(db_name=real_db))
        elif action == "list_db": 
            res = stub.ListDatabases(storage_pb2.EmptyReq())
            owner_prefix = f"{user['user']}_"
            mis_bds = [db.replace(owner_prefix, "", 1) for db in res.items if db.startswith(owner_prefix)]
            return {"message": "OK", "items": mis_bds}
        elif action == "delete_db": res = stub.DeleteDatabase(storage_pb2.DbReq(db_name=real_db))
        elif action == "create_table": res = stub.CreateTable(storage_pb2.TableReq(db_name=real_db, table_name=req.table_name))
        elif action == "list_table": res = stub.ListTables(storage_pb2.DbReq(db_name=real_db))
        elif action == "delete_table": res = stub.DeleteTable(storage_pb2.TableReq(db_name=real_db, table_name=req.table_name))
        else: raise HTTPException(400, "Acción no válida")
        return {"message": res.message, "items": list(getattr(res, 'items', []))}

@app.post("/insert")
def insert(req: InsertReq, user: dict = Depends(get_current_user)):
    if user.get("role") not in ["admin", "escritor"]: raise HTTPException(403, "Solo lectura")
    real_db = get_real_db(req.db_name, user)
    with grpc.insecure_channel('localhost:50052') as ch:
        res = storage_pb2_grpc.StorageServiceStub(ch).InsertRecord(storage_pb2.InsertRequest(db_name=real_db, table_name=req.table_name, data_json=json.dumps(req.data)))
        return {"message": res.message}

@app.post("/find")
def find(req: TableReq, user: dict = Depends(get_current_user)):
    real_db = get_real_db(req.db_name, user)
    with grpc.insecure_channel('localhost:50052') as ch:
        res = storage_pb2_grpc.StorageServiceStub(ch).FindRecords(storage_pb2.SearchRequest(db_name=real_db, table_name=req.table_name))
        if not res.success: raise HTTPException(400, res.message)
        return {"data": json.loads(res.data_json)}

@app.post("/update")
def update(req: UpdateReq, user: dict = Depends(get_current_user)):
    if user.get("role") not in ["admin", "escritor"]: raise HTTPException(403, "Solo lectura")
    real_db = get_real_db(req.db_name, user)
    with grpc.insecure_channel('localhost:50052') as ch:
        res = storage_pb2_grpc.StorageServiceStub(ch).UpdateRecords(storage_pb2.UpdateRequest(db_name=real_db, table_name=req.table_name, condition_key=req.condition_key, condition_value=req.condition_value, new_data_json=json.dumps(req.new_data)))
        return {"message": res.message}

@app.post("/delete")
def delete(req: DelReq, user: dict = Depends(get_current_user)):
    if user.get("role") not in ["admin", "escritor"]: raise HTTPException(403, "Solo lectura")
    real_db = get_real_db(req.db_name, user)
    with grpc.insecure_channel('localhost:50052') as ch:
        res = storage_pb2_grpc.StorageServiceStub(ch).DeleteRecords(storage_pb2.DeleteRequest(db_name=real_db, table_name=req.table_name, condition_key=req.condition_key, condition_value=req.condition_value))
        return {"message": res.message}

@app.post("/query")
def query(req: QueryReq, user: dict = Depends(get_current_user)):
    real_db = get_real_db(req.db_name, user)
    try:
        conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        ch = conn.channel()
        ch.queue_declare(queue='aggregation_tasks')
        ch.basic_publish(exchange='', routing_key='aggregation_tasks', body=json.dumps({"db_name": real_db, "table_name": req.table_name, "operation": req.operation}))
        conn.close()
        return {"message": "Consulta asíncrona encolada"}
    except: raise HTTPException(500, "Error MQ")

@app.post("/sql")
def execute_sql(req: SQLReq, user: dict = Depends(get_current_user)):
    q = req.query.strip()
    rol = user.get("role")
    
    match_sel = re.match(r"(?i)^SELECT\s+\*\s+FROM\s+([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)", q)
    if match_sel: return find(TableReq(db_name=match_sel.group(1), table_name=match_sel.group(2)), user)

    if rol not in ["admin", "escritor"]: raise HTTPException(403, "Tu rol no permite modificar datos mediante SQL")

    match_ins = re.match(r"(?i)^INSERT\s+INTO\s+([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\s+VALUES\s*\((.+)\)", q)
    if match_ins: return insert(InsertReq(db_name=match_ins.group(1), table_name=match_ins.group(2), data=json.loads(match_ins.group(3))), user)
    
    match_del = re.match(r"(?i)^DELETE\s+FROM\s+([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\s+WHERE\s+([a-zA-Z0-9_]+)\s*=\s*(.+)", q)
    if match_del: return delete(DelReq(db_name=match_del.group(1), table_name=match_del.group(2), condition_key=match_del.group(3), condition_value=match_del.group(4).strip("\"'")), user)
    
    raise HTTPException(400, "Sintaxis SQL no reconocida.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)