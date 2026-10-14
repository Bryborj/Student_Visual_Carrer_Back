import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import resolve_authenticated_user
from app.database import db

router = APIRouter(tags=["Forum"])

class ForumActionRequest(BaseModel):
    action: str
    postId: str | None = None
    title: str | None = None
    content: str | None = None
    category: str | None = None
    career: str | None = None
    username: str | None = None
    emailHash: str | None = None
    commentContent: str | None = None

def format_post(row: dict) -> dict:
    liked_by = row.get("liked_by", [])
    comments = row.get("comments", [])
    if isinstance(liked_by, str):
        liked_by = json.loads(liked_by)
    if isinstance(comments, str):
        comments = json.loads(comments)

    created_at = row.get("created_at")
    created_at_str = created_at.isoformat() if hasattr(created_at, "isoformat") else datetime.now(timezone.utc).isoformat()

    return {
        "_id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "category": row["category"],
        "career": row.get("career") or "General",
        "author": row["author"],
        "emailHash": row["email_hash"],
        "likes": row.get("likes", 0),
        "likedBy": liked_by,
        "comments": comments,
        "createdAt": created_at_str
    }

@router.get("/forum")
async def get_forum_posts(
    category: str | None = Query(None),
    career: str | None = Query(None)
):
    """Obtiene publicaciones del foro comunitario."""
    if not db.pool:
        raise HTTPException(status_code=500, detail="Database not connected.")

    async with db.pool.acquire() as conn:
        query = "SELECT * FROM forum_posts WHERE 1=1"
        params = []

        if category and category != "Todos":
            params.append(category)
            query += f" AND category = ${len(params)}"

        if career and career != "Todas":
            params.append(career)
            query += f" AND career = ${len(params)}"

        query += " ORDER BY created_at DESC LIMIT 50;"
        rows = await conn.fetch(query, *params)
        return [format_post(dict(r)) for r in rows]

@router.post("/forum")
async def handle_forum_action(
    req: ForumActionRequest,
    authorization: str | None = Header(None)
):
    """Maneja acciones del foro: create_post, like_post, add_comment."""
    if not db.pool:
        raise HTTPException(status_code=500, detail="Database not connected.")

    # Resolver identidad autenticada vía JWT o modo legado verificado en BD
    user = await resolve_authenticated_user(authorization, req.username, req.emailHash)
    author_username = user["username"]
    author_email_hash = user["emailHash"]

    action = req.action

    async with db.pool.acquire() as conn:
        # 1. CREAR POST
        if action == "create_post":
            if not req.title or not req.content or not req.category:
                raise HTTPException(status_code=400, detail="Título, contenido y categoría son requeridos.")

            new_id = str(uuid.uuid4())
            career = req.career or "General"

            row = await conn.fetchrow("""
                INSERT INTO forum_posts (
                    id, title, content, category, career, author, email_hash,
                    likes, liked_by, comments, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7,
                    0, '[]'::jsonb, '[]'::jsonb, NOW()
                ) RETURNING *;
            """, new_id, req.title, req.content, req.category, career, author_username, author_email_hash)

            return format_post(dict(row))

        # 2. DAR / QUITAR LIKE
        if action == "like_post":
            if not req.postId:
                raise HTTPException(status_code=400, detail="Post ID requerido.")

            post_row = await conn.fetchrow("SELECT * FROM forum_posts WHERE id = $1;", req.postId)
            if not post_row:
                raise HTTPException(status_code=404, detail="Post no encontrado.")

            post = dict(post_row)
            liked_by = post.get("liked_by", [])
            if isinstance(liked_by, str):
                liked_by = json.loads(liked_by)

            has_liked = author_email_hash in liked_by
            if has_liked:
                updated_liked_by = [e for e in liked_by if e != author_email_hash]
                likes_delta = -1
            else:
                updated_liked_by = [*liked_by, author_email_hash]
                likes_delta = 1

            upd_row = await conn.fetchrow("""
                UPDATE forum_posts
                SET likes = likes + $1,
                    liked_by = $2::jsonb
                WHERE id = $3
                RETURNING *;
            """, likes_delta, json.dumps(updated_liked_by), req.postId)

            return format_post(dict(upd_row))

        # 3. AÑADIR COMENTARIO
        if action == "add_comment":
            if not req.postId or not req.commentContent:
                raise HTTPException(status_code=400, detail="Post ID y comentario requeridos.")

            new_comment = {
                "id": str(uuid.uuid4()),
                "author": author_username,
                "emailHash": author_email_hash,
                "content": req.commentContent,
                "createdAt": datetime.now(timezone.utc).isoformat()
            }

            upd_row = await conn.fetchrow("""
                UPDATE forum_posts
                SET comments = COALESCE(comments, '[]'::jsonb) || $1::jsonb
                WHERE id = $2
                RETURNING *;
            """, json.dumps([new_comment]), req.postId)

            if not upd_row:
                raise HTTPException(status_code=404, detail="Post no encontrado.")

            return format_post(dict(upd_row))

    raise HTTPException(status_code=400, detail="Acción no válida.")
