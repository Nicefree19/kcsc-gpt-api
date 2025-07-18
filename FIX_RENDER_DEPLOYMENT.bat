@echo off
echo 🔧 Fixing Render deployment issues...
echo.

echo 1. Running path fix script...
python fix_render_paths.py

echo.
echo 2. Checking file structure...
if exist "search_index.json" (
    echo ✅ search_index.json found
) else (
    echo ❌ search_index.json missing
)

if exist "standards_split\split_index.json" (
    echo ✅ split_index.json found
) else (
    echo ❌ split_index.json missing
)

echo.
echo 3. Testing API server locally...
echo Starting test server on port 8000...
start /B python enhanced_gpts_api_server.py
timeout /t 5 /nobreak >nul

echo.
echo 4. Testing API endpoints...
curl -X GET "http://localhost:8000/health" -H "X-API-Key: kcsc-gpt-secure-key-2025"

echo.
echo 5. Stopping test server...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq enhanced_gpts_api_server*" >nul 2>&1

echo.
echo ✅ Fix completed! Ready for Render deployment.
echo.
echo 📋 Next steps:
echo 1. git add .
echo 2. git commit -m "Fix Render deployment paths"
echo 3. git push origin main
echo 4. Redeploy on Render
echo.
pause