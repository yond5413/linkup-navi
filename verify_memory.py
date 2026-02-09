import asyncio
import os
import sys

# Add backend to path
backend_path = os.path.join(os.getcwd()) if os.path.exists(os.path.join(os.getcwd(), "app")) else os.path.join(os.getcwd(), "backend")
sys.path.append(backend_path)

async def test_memory():
    from app.services.vector_memory import get_vector_memory_service
    from app.config import get_settings
    
    settings = get_settings()
    # Ensure env is loaded
    print(f"Cohere API Key exists: {bool(settings.cohere_api_key)}")
    
    service = get_vector_memory_service()
    
    # Test adding
    print("Adding to memory...")
    service.add_to_memory("The capital of France is Paris.")
    service.add_to_memory("The capital of Germany is Berlin.")
    service.add_to_memory("The capital of Italy is Rome.")
    
    # Test querying
    print("Querying memory for 'What is the capital of France?'...")
    results = service.query_memory("What is the capital of France?", top_k=2)
    print(f"Results: {results}")
    
    if "The capital of France is Paris." in results:
        print("Verification SUCCESSAL")
    else:
        print("Verification FAILED")

if __name__ == "__main__":
    asyncio.run(test_memory())
