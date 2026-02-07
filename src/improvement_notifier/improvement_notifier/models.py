from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Improvement(BaseModel):
    """
    Represents an improvement record from the database.
    Schema: public.improvement_read_model
    """

    id: int
    user_aggregate_id: str
    content: str
    created_at: datetime
    completed: bool = False
