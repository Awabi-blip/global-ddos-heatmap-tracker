from typing import Annotated
from fastapi import Depends, HTTPException, Request

async def verify_session(request: Request) -> int:
    val:str = request.session.get("session_id")
    if not val:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        session_id: int = int(val)  
    except ValueError:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Login required")
    else:
        return session_id

LoggedIn = Annotated[int, Depends(verify_session)]
