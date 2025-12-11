# Project Setup Instructions

## 1. Create a `.env` file

Create a `.env` file in the **parent directory** with the following content:

```
DB_USER="..."
DB_PASSWORD="..."
```

---

## 2. Backend Setup

Open your terminal and run the following commands:

```bash
cd backend
python -m venv venv
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 3. Frontend Setup

Open the `index.html` file in your browser.

After opening it, **start Command Gatewaying**.
