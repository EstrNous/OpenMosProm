from typing import Optional
from pydantic import BaseModel, Field

class PromptRequest(BaseModel):
    """Запрос для тестового обращения к ML-модели."""
    prompt: str = Field(..., description="Текст запроса, который отправляется в ML-модель")


class SimpleAnswer(BaseModel):
    """Простой ответ, возвращаемый после запроса к ML-модели."""
    answer: str = Field(..., description="Ответ, полученный от ML-модели")


class SupportRequest(BaseModel):
    """Модель входящего обращения пользователя в службу поддержки."""
    user_message: str = Field(..., description="Текст сообщения пользователя")
    user_id: str = Field(..., description="Уникальный идентификатор пользователя")
    timestamp: str = Field(..., description="Время создания обращения")
    channel: str = Field("web", description="Канал, из которого поступило обращение")


class SupportResponse(BaseModel):
    """Краткий ответ на создание обращения — возвращается клиенту."""
    ticket_id: int = Field(..., description="ID созданного тикета")
    dialog_id: int = Field(..., description="ID связанного диалога")
    status: str = Field(..., description="Текущий статус тикета")


class TicketCreateIn(BaseModel):
    """Входная модель для ручного создания тикета."""
    dialog_id: Optional[int] = Field(None, description="ID диалога, к которому относится тикет")
    type: Optional[str] = Field(None, description="Тип тикета")


class TicketOut(BaseModel):
    """Информация о тикете, возвращаемая наружу."""
    id: int = Field(..., description="Уникальный ID тикета")
    dialog_id: Optional[int] = Field(None, description="ID связанного диалога")
    status: str = Field(..., description="Статус тикета")
    created_at: Optional[str] = Field(None, description="Время создания тикета")
    resolved_at: Optional[str] = Field(None, description="Время закрытия тикета, если он решён")
    type: Optional[str] = Field(None, description="Тип тикета")

    class Config:
        orm_mode = True


class EnqueueIn(BaseModel):
    """Модель запроса для помещения тикета в очередь обработки ML."""
    dialog_id: int = Field(..., description="ID диалога, к которому относится тикет")
    type: Optional[str] = Field(None, description="Тип тикета (используется для маршрутизации в ML)")


class DequeueOut(BaseModel):
    """Ответ при выдаче тикета ML-воркеру из очереди."""
    ticket_id: int = Field(..., description="ID тикета, который выдан ML-воркеру")
    dialog_id: Optional[int] = Field(None, description="ID диалога, связанного с тикетом")
    status: str = Field(..., description="Текущий статус тикета")


class ResultIn(BaseModel):
    """Модель данных, с которыми ML возвращает результат решения тикета."""
    ticket_id: int = Field(..., description="ID тикета, к которому относится результат")
    result: Optional[dict] = Field(None, description="Результат работы ML-модели")
    solved: bool = Field(True, description="Флаг, показывающий, решён ли тикет")

class EnqueueResponse(BaseModel):
    ticket_id: int = Field(..., description="ID созданного тикета")

class DequeueResponse(BaseModel):
    ticket_id: int = Field(..., description="ID тикета")
    dialog_id: Optional[int] = Field(None, description="ID диалога")
    status: str = Field(..., description="Статус тикета")