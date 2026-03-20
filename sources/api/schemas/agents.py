from pydantic import BaseModel, Field


class PrepareMeetingRequest(BaseModel):
    """Запрос на подготовку к встрече с контактом."""
    query: str = Field("", description="Текст запроса, например: 'подготовь меня к встрече с Иваном Ивановым'",)
    contact_id: str = Field(..., description="ID контакта (выбирается на фронтенде из списка/автодополнения).", min_length=1,)
    

class PrepareMeetingSummary(BaseModel):
    """Сводка по контакту и истории общения."""
    profile: str = Field(..., description="Краткое описание человека: кто он, контекст знакомства.",)
    last_interactions: str = Field(...,description="Краткое резюме последних взаимодействий.",)
    promises: str = Field(..., description="Что вы обещали человеку и что он обещал вам.",)
    risks: str = Field(..., description="Чувствительные темы, риски недопонимания, моменты, о которых стоит помнить.",)


class PrepareMeetingAdvice(BaseModel):
    """Рекомендации по встрече."""
    talking_points: str = Field(..., description="Список тем, о которых стоит поговорить на встрече.",)
    followups: str = Field(..., description="Идеи для follow‑up после встречи (что зафиксировать, что отправить, о чём напомнить).",)
    draft_message: str | None = Field(None, description="Опциональный черновик письма/сообщения для контакта перед или после встречи.",)


class PrepareMeetingResponse(BaseModel):
    """Ответ агента подготовки к встрече."""
    contact_id: str = Field(..., description="ID выбранного контакта в Rockfile.")
    contact_name: str = Field(..., description="Имя контакта, понятное пользователю.")
    summary: PrepareMeetingSummary = Field(..., description="Сводка по контакту и истории взаимодействий.",)
    advice: PrepareMeetingAdvice = Field(..., description="Советы по встрече и follow‑up.",)
    raw_markdown: str = Field(..., description="Готовый markdown‑подобный текст, который можно сразу отобразить в UI.",)

