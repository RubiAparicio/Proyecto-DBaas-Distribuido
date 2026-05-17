import grpc
from concurrent import futures
import time, jwt, datetime, json, os, sys

sys.path.append('.')
import auth_pb2, auth_pb2_grpc

SECRET_KEY = "mi_clave_super_secreta_para_jwt_123"
USERS_FILE = "users.json"

# Al crear el archivo por primera vez, el admin "maestro" es su propio creador
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({"admin": {"password": "1234", "role": "admin", "creator": "admin"}}, f, indent=4)

class AuthService(auth_pb2_grpc.AuthServiceServicer):
    def Register(self, request, context):
        with open(USERS_FILE, 'r') as f: users = json.load(f)
        if request.username in users: return auth_pb2.RegisterResponse(success=False, message="El usuario ya existe.")
        
        # Guardamos al usuario y a su creador
        users[request.username] = {
            "password": request.password, 
            "role": request.role,
            "creator": request.creator
        }
        with open(USERS_FILE, 'w') as f: json.dump(users, f, indent=4)
        return auth_pb2.RegisterResponse(success=True, message=f"Usuario {request.username} creado.")

    def Login(self, request, context):
        with open(USERS_FILE, 'r') as f: users = json.load(f)
        user_data = users.get(request.username)
        
        if user_data and user_data["password"] == request.password:
            # Metemos al creador en el token como un tatuaje
            payload = {
                "user": request.username,
                "role": user_data["role"],
                "creator": user_data.get("creator", "admin"),
                "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
            return auth_pb2.LoginResponse(success=True, token=token, message="Login exitoso")
        return auth_pb2.LoginResponse(success=False, token="", message="Credenciales inválidas")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Auth Service en puerto 50051...")
    try:
        while True: time.sleep(86400)
    except KeyboardInterrupt: server.stop(0)

if __name__ == '__main__': serve()