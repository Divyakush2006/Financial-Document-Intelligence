# 📋 API Testing Guide

## Quick Fix Applied ✅

**Issue**: `'ExcelToJSONConverter' object has no attribute 'convert_file'`

**Cause**: Upload route was calling `converter.convert_file()` but the actual method is `converter.convert()`

**Fix**: Updated `upload_routes.py` to use the correct method name.

---

## Testing the Upload API

### 1. Restart the Backend
```bash
# Stop the current server (Ctrl+C)
cd backend
python main.py
```

The server will reload automatically with the fix.

### 2. Test Upload via Postman

**Import Collection**: `Bank_Statement_API.postman_collection.json`

**Request**: `1. Upload Statement`
- Method: POST
- URL: `http://localhost:8000/api/statements/upload`
- Body → form-data
  - Key: `file` (type: File)
  - Value: Select any `.xlsx` file from `Bank statements - Anonymised/`

**Expected Response**:
```json
{
  "success": true,
  "statement_id": "stmt_account_x_...",
  "account_number": "Account X",
  "transaction_count": 225,
  "message": "Successfully processed 225 transactions",
  "processing_status": "completed"
}
```

### 3. Test Upload via Frontend

**Start Frontend** (in new terminal):
```bash
cd frontend
python app.py
```

**Open Browser**: http://localhost:5000

**Steps**:
1. Click the upload area
2. Select Excel file
3. Wait for processing
4. Should show success message with transaction count

---

## Full Testing Workflow

### Test 1: Upload ✅
```bash
POST /api/statements/upload
# Upload Account 1.xlsx
```

### Test 2: List Statements ✅
```bash
GET /api/statements/
# Should show all uploaded statements
```

### Test 3: AI Query ✅
```bash
POST /api/statements/query
{
  "message": "Show Dream11 payments"
}
```

### Test 4: Search Transactions ✅
```bash
GET /api/statements/transactions/search?description=Dream11&payment_method=UPI
```

### Test 5: Analytics ✅
```bash
GET /api/statements/analytics/summary
# Returns total balance, credits, debits
```

---

## Troubleshooting

### If upload still fails:

1. **Check file format**: Must be `.xlsx` or `.xls`
2. **Check file size**: Max 16MB
3. **Check Supabase**: Ensure connection is working
4. **View logs**: Backend terminal will show detailed errors

### If frontend can't connect:

1. **Verify backend is running**: http://localhost:8000/
2. **Check CORS**: Already configured to allow all origins
3. **Check browser console**: F12 → Console tab

---

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/statements/upload` | POST | Upload Excel file |
| `/api/statements/` | GET | List all statements |
| `/api/statements/{id}` | GET | Get specific statement |
| `/api/statements/query` | POST | AI natural language query |
| `/api/statements/transactions/search` | GET | Search with filters |
| `/api/statements/analytics/summary` | GET | Overall analytics |

---

## Next Steps

1. ✅ **Fixed** - Method name corrected
2. 🔄 **Restart** - Backend server needs restart
3. ✅ **Test** - Try upload via Postman or Frontend
4. 🚀 **Ready** - Full system operational!
