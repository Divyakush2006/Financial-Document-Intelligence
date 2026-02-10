# 🏦 Financial Document Intelligence Platform

![Python Badge](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![FastAPI Badge](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Flask Badge](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask)
![Supabase Badge](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase)
![Docker Badge](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)
![License Badge](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

> **Enterprise-grade financial analytics powered by AI.** Transform raw bank statements into actionable intelligence with Natural Language Queries.

---

## 🚀 Overview

The **Financial Document Intelligence Platform** is a robust, scalable solution designed to automate the ingestion, extraction, and analysis of complex financial documents. By leveraging advanced **Backboard AI** for natural language understanding and high-precision OCR pipelines, it eliminates manual data reconciliation and provides instant financial insights.

Designed for high-volume environments, this platform serves fintech startups, credit underwriting teams, and financial analysts who require precision, speed, and security.

### 🌟 Key Differentiators

-   **Intelligent Document Processing (IDP)**: Hybrid rule-based and LLM-driven parsing for PDF/Excel statements.
-   **Natural Language Query Engine**: Ask complex financial questions in plain English (e.g., *"Calculate average monthly burn rate"*).
-   **Security-First Architecture**: Rigorous SQL injection prevention, XSS protection, and secure API endpoints.
-   **Real-Time Analytics**: Visual dashboards for spending trends, income verification, and category breakdowns.

---

## 🏗️ Architecture

```mermaid
graph TD
    User[User] -->|Uploads Statement| FE[Frontend (Flask)] 
    FE -->|POST /upload| API[Backend API (FastAPI)]
    
    subgraph Extraction Service
        API -->|Excel/PDF| Parser[Document Parser]
        Parser -->|Raw Data| Validator[Data Validator]
        Validator -->|Sanitized Data| DB[(Supabase DB)]
    end
    
    subgraph Intelligence Engine
        User -->|Asks Question| FE
        FE -->|POST /query| NLP[NL Query Processor]
        NLP -->|Context| LLM[Backboard AI]
        LLM -->|SQL/Filters| DB
        DB -->|Results| Response[Formatter]
        Response -->|JSON/Visuals| FE
    end
```

---

## 🧗 Challenges Faced & Solutions

### 1. Handling Heavy Extraction Loads
**Challenge:** Processing large PDF/Excel statements with thousands of transactions often caused timeouts or UI freezes in a monolithic architecture.
**Solution:** The system follows a microservices-oriented architecture, separating the heavy extraction logic from the user-facing query engine. This ensures the dashboard remains responsive even while heavy background processing occurs.

### 2. LLM Hallucinations on Financial Data
**Challenge:** Generic LLMs often "hallucinate" numbers or invent transactions when asked specific questions.
**Solution:** We implemented a **RAG (Retrieval-Augmented Generation)** pipeline where the LLM only generates SQL queries or filters based on strict schemas, never answering directly from its training data. This ensures 100% data accuracy.

### 3. Diverse Bank Statement Formats
**Challenge:** Every bank uses a different layout, date format, and column structure, making rule-based parsing brittle.
**Solution:** Developed a **Hybrid Parser** that uses regex heuristics for common formats and falls back to an LLM-vision approach for unstructured documents, creating a robust universal ingestion engine.

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend** | **FastAPI** | High-performance, async-ready web framework for API services. |
| **Frontend** | **Flask** | Lightweight WSGI web application framework for the dashboard. |
| **Database** | **Supabase** | Open source Firebase alternative based on PostgreSQL. |
| **AI / LLM** | **Backboard AI** | Advanced LLM integration for natural language understanding. |
| **OCR** | **Azure / EasyOCR** | Optical Character Recognition for scanned PDF documents. |
| **Storage** | **Cloudinary** | Scalable cloud storage for document management. |

---

## ⚡ Features

### 1. Universal Document Support
Seamlessly processes diverse formats including PDF bank statements and Excel reports, handling varying layouts and structures automatically with high fault tolerance.

### 2. Deep Financial Insights
Go beyond simple transaction lists. The platform calculates:
*   **Monthly Burn Rate**
*   **Income Stability Score**
*   **Category-wise Spending Analysis**
*   **Recurring Subscription Detection**

### 3. Secure Query Interface
Built with an "Enterprise-First" security mindset:
*   **Input Sanitization**: Advanced regex filters for SQLi/XSS.
*   **Rate Limiting**: Protects resources from abuse.
*   **Error Handling**: Standardized, opaque error responses to prevent information leakage.

---

## 🚀 Installation & Deployment

### Prerequisites
*   Python 3.8+
*   Supabase Project Credentials
*   API Keys (Google Cloud, Backboard AI)

### Quick Start

1.  **Clone the repository**
    ```bash
    git clone https://github.com/Divyakush2006/Financial-Document-Intelligence.git
    cd Financial-Document-Intelligence
    ```

2.  **Environment Setup**
    Create a `.env` file in the root directory:
    ```env
    # Database
    SUPABASE_URL=your_supabase_url
    SUPABASE_KEY=your_supabase_key

    # AI Services
    BACKBOARD_API_KEY=your_key
    
    # Storage
    CLOUDINARY_CLOUD_NAME=your_cloud_name
    CLOUDINARY_API_KEY=your_api_key
    CLOUDINARY_API_SECRET=your_api_secret
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r backend/requirements.txt
    pip install -r frontend/requirements.txt
    ```

4.  **Launch Services**
    *Terminal 1 (Backend API):*
    ```bash
    cd backend
    python main.py
    ```
    *Terminal 2 (Dashboard):*
    ```bash
    cd frontend
    python app.py
    ```

5.  **Access the Dashboard**
    Open `http://localhost:5000` to interact with the platform.

---

## 📚 API Documentation

Detailed API documentation is available via Swagger UI once the backend is running:
*   **Swagger UI**: `http://localhost:8000/docs`
*   **ReDoc**: `http://localhost:8000/redoc`

### Core Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/statements/upload` | Upload and process bank statements. |
| `POST` | `/api/statements/query` | Natural language query interface. |
| `GET` | `/api/statements/` | Retrieve list of processed statements. |
| `GET` | `/api/transactions/search` | Advanced search with filters. |

---

## 🤝 Contributing

We welcome contributions to enhance the platform!
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'feat: Add AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

---

<p align="center">
  <b>Built for Scalability, Security, and Intelligence.</b>
  <br>
  Developed by <a href="https://github.com/Divyakush2006">Divyakush Punjabi</a>
</p>
