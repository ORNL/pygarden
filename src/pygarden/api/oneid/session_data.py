from pydantic import BaseModel

class SessionData(BaseModel):
    user_id: int
    email: str
    first_name: str
    last_name: str
    us_citizen: bool
    affiliation: str
    admin: bool
