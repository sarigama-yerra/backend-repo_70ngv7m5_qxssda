import os
import io
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from PIL import Image, ImageOps
import qrcode
import qrcode.constants as qconst
from database import create_document
from schemas import Qr

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


EC_MAP = {
    "L": qconst.ERROR_CORRECT_L,
    "M": qconst.ERROR_CORRECT_M,
    "Q": qconst.ERROR_CORRECT_Q,
    "H": qconst.ERROR_CORRECT_H,
}

class QRRequest(BaseModel):
    content: str
    fill_color: str = "#111827"
    back_color: str = "#ffffff"
    box_size: int = 10
    border: int = 4
    error_correction: str = "M"  # L, M, Q, H
    rounded: bool = True
    logo_url: Optional[str] = None


def _rounded_square(mask: Image.Image, radius: int = 6):
    """Apply rounded corners to the black modules mask."""
    from PIL import ImageFilter, ImageDraw

    mask = mask.convert("L")
    w, h = mask.size
    # Slight blur to soften corners after downsample
    draw = ImageDraw.Draw(mask)
    # Create a rounded rectangle over every module grid by downscaling trick
    # For simplicity, just blur mask to achieve soft edges
    mask = mask.filter(ImageFilter.GaussianBlur(radius=radius/3))
    return mask


def _fetch_logo(url: str) -> Optional[Image.Image]:
    try:
        import requests
        resp = requests.get(url, timeout=6)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        return img
    except Exception:
        return None


@app.get("/")
def read_root():
    return {"message": "QR Code API ready"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Connected"
    except Exception as e:
        response["database"] = f"❌ {e}"
    return response


@app.post("/api/qrcode.png")
def generate_qr_png(payload: QRRequest):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    ec = EC_MAP.get(payload.error_correction.upper(), qconst.ERROR_CORRECT_M)
    qr = qrcode.QRCode(
        error_correction=ec,
        box_size=payload.box_size,
        border=payload.border,
    )
    qr.add_data(payload.content)
    qr.make(fit=True)
    img = qr.make_image(fill_color=payload.fill_color, back_color=payload.back_color).convert("RGBA")

    if payload.rounded:
        # Create mask from the QR to soften corners
        alpha = img.split()[-1]
        alpha = _rounded_square(alpha, radius=max(4, payload.box_size))
        img.putalpha(alpha)

    if payload.logo_url:
        logo = _fetch_logo(payload.logo_url)
        if logo:
            # Scale logo to about 18% of QR width
            q_w, q_h = img.size
            target = int(min(q_w, q_h) * 0.2)
            logo = ImageOps.contain(logo, (target, target))
            # Add small white background circle/square for contrast
            bg = Image.new("RGBA", (logo.width + 16, logo.height + 16), (255, 255, 255, 220))
            bg_pos = ((img.width - bg.width)//2, (img.height - bg.height)//2)
            img.alpha_composite(bg, bg_pos)
            pos = ((img.width - logo.width)//2, (img.height - logo.height)//2)
            img.alpha_composite(logo, pos)

    # Persist request for history
    try:
        create_document("qr", Qr(**payload.model_dump()))
    except Exception:
        pass

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


class HistoryItem(BaseModel):
    content: str
    fill_color: str
    back_color: str
    box_size: int
    border: int
    error_correction: str
    logo_url: Optional[str] = None


@app.get("/api/history")
def get_history(limit: int = Query(12, ge=1, le=50)):
    try:
        from database import get_documents
        docs = get_documents("qr", {}, limit)
        # Normalize fields
        out: List[HistoryItem] = []
        for d in docs:
            out.append(HistoryItem(
                content=d.get("content", ""),
                fill_color=d.get("fill_color", "#111827"),
                back_color=d.get("back_color", "#ffffff"),
                box_size=int(d.get("box_size", 10)),
                border=int(d.get("border", 4)),
                error_correction=str(d.get("error_correction", "M")),
                logo_url=d.get("logo_url")
            ))
        return JSONResponse([i.model_dump() for i in out])
    except Exception:
        return JSONResponse([])


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
