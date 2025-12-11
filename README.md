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

## 4. Additional Features

- Show a clear explanation for why a command was rejected.  
- Provide a list of all available rules.  
- Allow logs to be sorted by time or by status (Accepted or Rejected).  
- In the admin log view, allow filtering logs by user type (user or admin).  
- Enable admins to search logs by entering another user’s or admin’s API key.

## 5. Demo Video

You can view the demo video here:  
[Demo Video (Google Doc Link)](https://docs.google.com/document/d/1-b3F8uqVpk0l62baEQ2dI_wrUWvFWrK7605DHCLe39s/edit?usp=sharing)

