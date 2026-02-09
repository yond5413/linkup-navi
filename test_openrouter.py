import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.llm import LLMClient
from unittest.mock import MagicMock, patch

async def test_llm_integration():
    print("Testing LLMClient with OpenRouter...")
    
    # Mock settings to use OpenRouter with a dummy key
    with patch('app.services.llm.get_settings') as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.llm_provider = "openrouter"
        mock_settings.openrouter_api_key = "sk-or-test-key"
        mock_settings.openrouter_model = "arcee-ai/trinity-large-preview:free"
        mock_get_settings.return_value = mock_settings
        
        client = LLMClient()
        print(f"Provider: {client.provider}")
        print(f"Model: {client.model}")
        
        # Mock OpenAI response
        with patch.object(client.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response from OpenRouter"
            mock_create.return_value = mock_response
            
            # Test generate
            print("\nTesting generate()...")
            response = client.generate("Hello")
            print(f"Response: {response}")
            if response == "Test response from OpenRouter":
                print("✅ generate() works")
            
            # Test generate_json
            print("\nTesting generate_json()...")
            mock_response.choices[0].message.content = '{"test": "json_response"}'
            json_response = client.generate_json("Respond in JSON", {"test": "string"})
            print(f"JSON Response: {json_response}")
            if json_response.get("test") == "json_response":
                print("✅ generate_json() works")

if __name__ == "__main__":
    asyncio.run(test_llm_integration())
