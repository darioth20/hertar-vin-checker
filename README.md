# HERTAR AUTOMOTIVE REPORT

## Local
```powershell
py -m pip install -r requirements.txt
py -m playwright install chromium
python app.py
```

Open:
`http://127.0.0.1:5000/lot/JM3KE4DY7F0550426`

## Render
Build Command:
```bash
pip install -r requirements.txt && python -m playwright install chromium
```

Start Command:
```bash
gunicorn app:app --timeout 180
```

Environment variables:
- VERCEL_EMAIL
- VERCEL_PASSWORD
- MARKETCHECK_API_KEY
- OPENAI_API_KEY
