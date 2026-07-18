from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Since api.py actually includes routers and is treated as the main app by uvicorn usually, 
# let's just restore the basic one seen in the disassembly.
# In reality, this main.py might just be a healthcheck while api.py is the main API.
app = FastAPI(title='Compliance API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

@app.get('/')
def read_root():
    return {'message': 'Welcome to the Compliance API'}

@app.get('/api/health')
def health_check():
    return {'status': 'ok'}
