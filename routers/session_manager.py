from sqlalchemy.orm import Session
import models
import json

def get_or_create_session(db: Session, session_id: str, phone_number: str):
    """Retrieves an active session state or creates a new one if it doesn't exist."""
    session_record = db.query(models.UssdSession).filter(models.UssdSession.session_id == session_id).first()
    
    if not session_record:
        session_record = models.UssdSession(
            session_id=session_id,
            phone_number=phone_number,
            current_state="MAIN_MENU",
            session_data=json.dumps({})
        )
        db.add(session_record)
        db.commit()
        db.refresh(session_record)
        
    return session_record

def update_session_state(db: Session, session_id: str, next_state: str, new_data: dict = None):
    """Updates the active menu state and merges incoming payload data."""
    session_record = db.query(models.UssdSession).filter(models.UssdSession.session_id == session_id).first()
    if session_record:
        session_record.current_state = next_state
        if new_data:
            current_data = json.loads(session_record.session_data) if session_record.session_data else {}
            current_data.update(new_data)
            session_record.session_data = json.dumps(current_data)
        db.commit()