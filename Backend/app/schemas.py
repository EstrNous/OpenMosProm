from typing import Optional, Literal, Dict, Any, List
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


class MLCallback(BaseModel):
    """
    Общая структура callback'а от ML.
    Ожидаем, что ML пришлёт ticket_id (наш dialog_id), action_type и payload.
    """
    ticket_id: int = Field(..., description="ID тикета (в нашей системе это dialog_id)")
    action_type: Literal["answer", "escalate", "call_tool"] = Field(..., description="Действие, которое предлагает ML")
    payload: Optional[Dict[str, Any]] = Field(None, description="Содержимое результата — зависит от action_type")
    user_query: Optional[str] = Field(None, description="Оригинальный вопрос пользователя")

class ToolModel(BaseModel):
    """
    Pydantic-схема для модели Tool (таблица tools).
    Используется для возврата данных об инструменте.
    """
    id: int = Field(..., description="Уникальный идентификатор инструмента")
    name: str = Field(..., description="Уникальное имя инструмента")
    description: Optional[str] = Field(None, description="Описание инструмента")
    created_at: Optional[str] = Field(None, description="Время создания записи в ISO-формате")

    class Config:
        orm_mode = True


class ToolInvocationModel(BaseModel):
    """
    Pydantic-схема для записи вызова инструмента (таблица tool_invocations).
    Используется для возврата деталей каждого вызова.
    """
    id: int = Field(..., description="Уникальный идентификатор вызова")
    tool_id: int = Field(..., description="ID инструмента")
    dialog_id: Optional[int] = Field(None, description="ID связанного диалога")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Параметры вызова инструмента")
    result: Optional[Dict[str, Any]] = Field(None, description="Результат выполнения инструмента")
    created_at: Optional[str] = Field(None, description="Время создания записи в ISO-формате")

    class Config:
        orm_mode = True


class MLWorkerResult(BaseModel):
    dialog_id: int = Field(..., description="ID тикета (dialog_id)")
    status: Literal["processed", "error"] = Field(..., description="processed | error")
    ml_result: Optional[Dict[str, Any]] = Field(None, description="Результат ML (при status=processed)")
    error_message: Optional[str] = Field(None, description="Текст ошибки (при status=error)")
