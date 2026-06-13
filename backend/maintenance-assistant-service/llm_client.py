import requests
import logging

logger = logging.getLogger('ollama-client')


class OllamaClient:
    def __init__(self, base_url, model='tinyllama'):
        self.base_url = base_url.rstrip('/')
        self.model = model

    def generate(self, prompt, system_prompt=None):
        """Generate a response using Ollama LLM"""
        try:
            payload = {
                'model': self.model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.3,
                    'top_p': 0.9,
                    'num_predict': 512
                }
            }
            if system_prompt:
                payload['system'] = system_prompt

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=300
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'No response generated.')
            else:
                logger.error(f"Ollama returned status {response.status_code}: {response.text}")
                return self._fallback_response(prompt)

        except requests.exceptions.ConnectionError:
            logger.warning("Ollama is not available, using fallback response")
            return self._fallback_response(prompt)
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return self._fallback_response(prompt)

    def _fallback_response(self, prompt):
        """Provide a rule-based fallback when Ollama is unavailable"""
        return (
            "I'm currently unable to connect to the AI model. "
            "Based on the available data, I recommend reviewing the maintenance logs "
            "and rental history for this bicycle. Bikes with high rental counts and "
            "infrequent servicing should be prioritized for maintenance. "
            "Please check the risk scores on the dashboard for automated recommendations."
        )

    def is_available(self):
        """Check if Ollama server is reachable"""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

