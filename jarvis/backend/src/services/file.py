import os
import uuid
import shutil
import mimetypes
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.config import get_settings
from ..models.file import File

settings = get_settings()

WORKSPACE_ROOT = Path.cwd().resolve()
MAX_INLINE_CONTENT_BYTES = 200 * 1024
IGNORED_NAMES = {
    ".git",
    ".venv",
    ".storage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "artifacts",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "__pycache__",
}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".log", ".sqlite", ".db"}
SECRET_NAMES = {".env"}


def _file_type(path: Path, mime_type: str | None) -> str:
    suffix = path.suffix.lower()
    if mime_type and mime_type.startswith("image/"):
        return "image"
    if mime_type and mime_type.startswith("video/"):
        return "video"
    if mime_type and mime_type.startswith("audio/"):
        return "audio"
    if suffix in {".md", ".markdown", ".mdx"}:
        return "markdown"
    if suffix in {
        ".css",
        ".html",
        ".js",
        ".jsx",
        ".json",
        ".py",
        ".ts",
        ".tsx",
        ".txt",
        ".yml",
        ".yaml",
    }:
        return "code" if suffix != ".txt" else "text"
    if suffix == ".pdf":
        return "pdf"
    return "text"


def _should_ignore(path: Path) -> bool:
    return (
        path.name in IGNORED_NAMES
        or path.name in SECRET_NAMES
        or path.name.startswith(".env.")
        or path.suffix.lower() in IGNORED_SUFFIXES
    )


def _read_inline_content(path: Path, size: int) -> str | None:
    if size > MAX_INLINE_CONTENT_BYTES:
        return f"File is {size:,} bytes. Open it from disk for full contents."

    mime_type, _ = mimetypes.guess_type(path.name)
    file_kind = _file_type(path, mime_type)
    if file_kind in {"image", "video", "audio", "pdf"}:
        return f"{mime_type or file_kind} file, {size:,} bytes"

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Binary file, {size:,} bytes"

class FileService:
    @staticmethod
    def get_workspace_tree(max_depth: int = 4) -> list[dict]:
        def build_node(path: Path, depth: int) -> dict | None:
            if _should_ignore(path):
                return None

            stat = path.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            relative_path = path.relative_to(WORKSPACE_ROOT).as_posix()
            display_path = "/" if relative_path == "." else f"/{relative_path}"

            if path.is_dir():
                children = []
                if depth < max_depth:
                    for child in sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
                        node = build_node(child, depth + 1)
                        if node:
                            children.append(node)

                return {
                    "name": path.name or WORKSPACE_ROOT.name,
                    "path": display_path,
                    "isDirectory": True,
                    "type": "directory",
                    "size": 0,
                    "modifiedAt": modified_at,
                    "children": children,
                }

            mime_type, _ = mimetypes.guess_type(path.name)
            size = stat.st_size
            return {
                "name": path.name,
                "path": display_path,
                "isDirectory": False,
                "type": _file_type(path, mime_type),
                "size": size,
                "modifiedAt": modified_at,
                "content": _read_inline_content(path, size),
            }

        nodes = []
        for child in sorted(WORKSPACE_ROOT.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            node = build_node(child, 0)
            if node:
                nodes.append(node)
        return nodes

    @staticmethod
    async def save_file(db: AsyncSession, project_id: str, upload_file: UploadFile) -> File:
        # Prevent path traversal in filename
        filename = os.path.basename(upload_file.filename or "unnamed_file")
        file_id = str(uuid.uuid4())
        
        # Create project sub-folder in storage path
        project_dir = settings.STORAGE_DIR / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Build path and write file
        target_path = project_dir / f"{file_id}_{filename}"
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        # Get file size
        size = os.path.getsize(target_path)
        
        # Relativize path for database representation
        relative_path = os.path.relpath(target_path, settings.STORAGE_DIR)
        
        file_record = File(
            id=file_id,
            project_id=project_id,
            filename=filename,
            path=relative_path,
            size=size,
            mime_type=upload_file.content_type or "application/octet-stream"
        )
        db.add(file_record)
        await db.flush()
        return file_record

    @staticmethod
    async def get_files(db: AsyncSession, project_id: str) -> List[File]:
        result = await db.execute(select(File).where(File.project_id == project_id))
        return list(result.scalars().all())

    @staticmethod
    async def get_file(db: AsyncSession, file_id: str) -> Optional[File]:
        return await db.get(File, file_id)

    @staticmethod
    async def delete_file(db: AsyncSession, file_id: str) -> bool:
        file_record = await db.get(File, file_id)
        if not file_record:
            return False
            
        # Remove physical file
        full_path = settings.STORAGE_DIR / file_record.path
        if os.path.exists(full_path):
            os.remove(full_path)
            
        await db.delete(file_record)
        await db.flush()
        return True
