# Financial Document Intelligence Platform

AI-powered invoice extraction, validation, and analytics system for DEVSoC Challenge 2.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Tesseract OCR (optional, for fallback)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your API keys

# Run server
python main.py
```

Server runs at: `http://localhost:8000`

### Test OCR Endpoint

```bash
# Using curl
curl -X POST "http://localhost:8000/api/ocr/extract" \
  -F "file=@path/to/invoice.jpg"
```

## 📁 Project Structure

```
Financial-Document-Intelligence/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example           # Environment template
│   └── services/
│       └── ocr_service.py     # OCR extraction
├── frontend/                   # (Coming soon)
└── README.md
```

## 🔧 Tech Stack

- **Backend**: FastAPI, Python
- **OCR**: EasyOCR, Tesseract
- **LLM**: Groq (Llama 3.1)
- **Database**: Supabase
- **Storage**: Cloudinary
- **ML**: scikit-learn

## 📝 API Endpoints

### `POST /api/ocr/extract`
Extract text from invoice image

**Request**: Multipart form with image file

**Response**:
```json
{
  "success": true,
  "text": "Invoice #12345...",
  "confidence": 0.95,
  "engine": "easyocr",
  "filename": "invoice.jpg"
}
```

## ⚙️ Configuration

See `.env.example` for required environment variables.

## 🏗️ Development Status

- [x] OCR Service
- [ ] LLM Extraction
- [ ] Database Integration
- [ ] Anomaly Detection
- [ ] Frontend Dashboard
