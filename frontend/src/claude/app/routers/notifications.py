from fastapi import APIRouter, HTTPException, Query
from typing import List

from .. import db
from ..schemas.notifications import NotificationOut, NotificationCreate

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=List[NotificationOut])
async def list_notifications(user_id: str = Query(...)):
    rows = await db.fetch(
        """
        SELECT id, user_id, type, title, message, related_patient_id,
               related_type, related_id, is_read, created_at
        FROM notifications
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 100
        """,
        user_id,
    )
    return [dict(r) for r in rows]


@router.get("/unread-count")
async def unread_count(user_id: str = Query(...)):
    row = await db.fetchrow(
        "SELECT COUNT(*) AS count FROM notifications WHERE user_id = $1 AND is_read = false",
        user_id,
    )
    return {"count": row["count"] if row else 0}


@router.post("", response_model=NotificationOut)
async def create_notification(payload: NotificationCreate):
    row = await db.fetchrow(
        """
        INSERT INTO notifications (user_id, type, title, message, related_patient_id, related_type, related_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, user_id, type, title, message, related_patient_id, related_type, related_id, is_read, created_at
        """,
        payload.user_id,
        payload.type,
        payload.title,
        payload.message,
        payload.related_patient_id,
        payload.related_type,
        payload.related_id,
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create notification")
    return dict(row)


@router.put("/{notification_id}/read")
async def mark_read(notification_id: str, user_id: str = Query(...)):
    result = await db.execute(
        """
        UPDATE notifications
        SET is_read = true, read_at = NOW()
        WHERE id = $1 AND user_id = $2
        """,
        notification_id,
        user_id,
    )
    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "ok"}


@router.put("/read-all")
async def mark_all_read(user_id: str = Query(...)):
    await db.execute(
        "UPDATE notifications SET is_read = true, read_at = NOW() WHERE user_id = $1",
        user_id,
    )
    return {"status": "ok"}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, user_id: str = Query(...)):
    result = await db.execute(
        "DELETE FROM notifications WHERE id = $1 AND user_id = $2",
        notification_id,
        user_id,
    )
    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "ok"}
