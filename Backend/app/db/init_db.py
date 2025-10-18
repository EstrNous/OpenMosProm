from .models import *
from .session import engine

print("Инициализация базы данных...")
Base.metadata.create_all(bind=engine)
print("Таблицы успешно созданы!")
