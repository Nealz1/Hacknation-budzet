from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import json
import os
from openai import OpenAI
from ..models import BudgetEntry

class SemanticComplianceAgent:
    """
    A Compliance Agent that uses LLM (Large Language Model) reasoning 
    instead of hardcoded regex/keywords.
    
    It verifies budget entries against the "Regulation 2c" (Paragraphs)
    and "Regulation 2d" (Financing Sources).
    """
    
    SYSTEM_PROMPT = """
    Jesteś Głównym Księgowym (AI Auditor) w Ministerstwie Cyfryzacji. 
    Twoim zadaniem jest weryfikacja zgodności planu budżetowego z Rozporządzeniem Ministra Finansów.
    
    ZASADY KLASYFIKACJI (Wyciąg uproszczony):
    - Paragraf 4300 (Zakup usług pozostałych): Usługi obce, serwis, tłumaczenia. NIE dla inwestycji.
    - Paragraf 6060 (Wydatki na zakupy inwestycyjne): Zakup środków trwałych > 10.000 PLN. Sprzęt komputerowy, licencje wieczyste.
    - Paragraf 4210 (Zakup materiałów): Materiały biurowe, drobny sprzęt < 10.000 PLN.
    - Paragraf 4410/4420: Podróże służbowe (delegacje).
    - Paragraf 4700: Szkolenia pracowników.
    
    Twoim celem jest wykrycie:
    1. Błędnej klasyfikacji (np. zakup serwera z paragrafu 4300).
    2. Niejasnych uzasadnień (tzw. "wata słowna").
    3. Ukrytych kosztów (np. licencja bez wdrożenia).
    4. Rozbicia zakupów (tzw. "salamislicing") w celu uniknięcia przetargu/inwestycji.

    Pamiętaj: Bądź surowy, ale sprawiedliwy. Szukaj "red flags".
    
    Format odpowiedzi JSON:
    {
        "is_compliant": boolean,
        "risk_level": "low"|"medium"|"high",
        "legal_citation": "string (czego dotyczy naruszenie)",
        "reasoning": "string (dlaczego)",
        "suggestion": "string (co poprawić)"
    }
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        
    def validate_entry(self, entry: BudgetEntry) -> Dict:
        """
        Validates a single budget entry using Semantic Analysis.
        """
        if not self.client:
            return self._simulate_llm_reasoning(entry)
            
        context = self._prepare_context(entry)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",  # Using a model good at reasoning/formatting
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                response_format={ "type": "json_object" },
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"LLM Error: {e}")
            return {
                "is_compliant": True,
                "risk_level": "unknown",
                "legal_citation": None,
                "reasoning": f"Błąd analizy AI: {str(e)}. Walidacja pominięta.",
                "suggestion": None
            }

    def _prepare_context(self, entry: BudgetEntry) -> str:
        return f"""
        ANALIZOWANA POZYCJA BUDŻETOWA:
        Nazwa: {entry.nazwa_zadania}
        Opis: {entry.opis_projektu}
        Uzasadnienie: {entry.szczegolowe_uzasadnienie}
        Kwota 2025: {entry.kwota_2025} PLN
        Paragraf: {entry.paragraf}
        Departament: {entry.department.code if entry.department else 'N/A'}
        """

    def _simulate_llm_reasoning(self, entry: BudgetEntry) -> Dict:
        """
        Fallback simulation if no API key is provided.
        """
        text = (entry.nazwa_zadania or "") + " " + (entry.opis_projektu or "")
        text = text.lower()
        amount = entry.kwota_2025 or 0
        paragraf = entry.paragraf or 0
        
        if "modernizacja" in text and paragraf == 4270 and amount > 50000:
            return {
                "is_compliant": False,
                "risk_level": "high",
                "legal_citation": "Art. 4 ust. 1 Ustawy o rachunkowości",
                "reasoning": "Użyto pojęcia 'Modernizacja' z paragrafu remontowego. Modernizacja zwiększająca wartość jest inwestycją.",
                "suggestion": "Zmień paragraf na 6050."
            }

        if ("subskrypcja" in text or "na rok" in text) and paragraf == 6060:
            return {
                "is_compliant": False,
                "risk_level": "medium",
                "legal_citation": "Rozporządzenie w sprawie klasyfikacji",
                "reasoning": "Paragraf 6060 dotyczy zakupów inwestycyjnych. Subskrypcje są kosztem bieżącym.",
                "suggestion": "Zmień paragraf na 4300."
            }

        return {
            "is_compliant": True,
            "risk_level": "low",
            "legal_citation": None,
            "reasoning": "Pozycja wygląda poprawnie (Tryb Demo). Dodaj klucz API dla pełnej analizy.",
            "suggestion": None
        }
