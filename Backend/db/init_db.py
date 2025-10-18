from Backend.db.session import engine, Base
from Backend.db.models import *

print("Инициализация базы данных...")
Base.metadata.create_all(bind=engine)
print("Таблицы успешно созданы!")
