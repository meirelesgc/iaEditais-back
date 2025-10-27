import asyncio
import selectors
import sys
import os

# Configurar event loop para Windows ANTES de importar qualquer coisa
if sys.platform == 'win32':
    # Definir política de event loop compatível com psycopg
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Agora importar e executar o uvicorn
if __name__ == "__main__":
    import uvicorn
    
    # Configurar variáveis de ambiente se necessário
    os.environ.setdefault('PYTHONPATH', '.')
    
    # Executar uvicorn com configurações específicas
    uvicorn.run(
        "iaEditais.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        loop="asyncio"
    )