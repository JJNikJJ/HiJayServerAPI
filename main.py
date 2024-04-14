from fastapi import FastAPI, HTTPException, Response, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from starlette.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import auth, db as firebase_db
from typing import List


# Инициализация Firebase
from firebase_config import initialize_firebase
initialize_firebase()

app = FastAPI()

# Добавление CORS Middleware для разрешения кросс-доменных запросов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Маршруты для аутентификации пользователя
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Классы Pydantic для описания структур данных
class UserCreate(BaseModel):
    email: str
    password: str

class UserPublic(BaseModel):
    id: int
    email: str

class ChatMessage(BaseModel):
    from_user_id: str
    to_user_id: str
    text: str

# API маршруты
@app.post("/register/")
async def register(user_details: UserCreate):
    """ Регистрирует нового пользователя в Firebase Auth. """
    try:
        user_record = auth.create_user(
            email=user_details.email,
            password=user_details.password
        )
        return {"uid": user_record.uid, "email": user_details.email}
    except auth.AuthError as e:
        raise HTTPException(status_code=400, detail="Firebase Auth error")

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """ Аутентификация пользователя и возврат токена. """
    try:
        user_record = auth.get_user_by_email(form_data.username)
        if not user_record:
            raise HTTPException(status_code=404, detail="User not found")
        # Проверка пароля здесь должна быть реализована через вашу собственную логику
        # В Firebase пароли не хранятся и не проверяются на сервере напрямую
        return {"access_token": user_record.uid, "token_type": "bearer"}
    except auth.AuthError:
        raise HTTPException(status_code=401, detail="Authentication failed")


@app.get("/users/", response_model=List[dict])
async def read_users():
    """ Извлекаем список пользователей из Firebase и выводим список всех пользователей """
    try:
        users = auth.list_users().iterate_all()
        users_list = []
        for user in users:
            # Преобразуем данные пользователя в словарь и добавляем в список
            users_list.append({
                'uid': user.uid,
                'email': user.email
                # Можно добавить больше полей по мере необходимости
            })
        return users_list
    except firebase_admin.exceptions.FirebaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user-profile", response_model=UserPublic)
def user_profile(user_id: str = Depends(oauth2_scheme)):
    """ Возвращает профиль текущего пользователя. """
    try:
        user = auth.get_user(user_id)
        return {"id": user.uid, "email": user.email}
    except auth.AuthError:
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/send-message/{chat_id}/")
async def send_message(chat_id: str, message: ChatMessage):
    """ Отправляет сообщение между пользователями и сохраняет его в Firebase. """
    ref = firebase_db.reference(f'chats/{chat_id}')
    new_message_ref = ref.push({
        'from_user_id': message.from_user_id,
        'to_user_id': message.to_user_id,
        'text': message.text,
        'timestamp': datetime.utcnow().isoformat()
    })
    if not new_message_ref.key:
        raise HTTPException(status_code=500, detail="Failed to send message")
    return {"success": True, "message_id": new_message_ref.key}

@app.get("/messages/{chat_id}/")
async def get_messages(chat_id: str):
    """ Получает сообщения из чата по идентификатору чата. """
    ref = firebase_db.reference(f'chats/{chat_id}')
    messages = ref.get()
    return list(messages.values()) if messages else []

@app.get("/test")
async def test_connection():
    """ Получает сообщение от сервера при подключении. """
    return {"message": "Server is up and running!"}

