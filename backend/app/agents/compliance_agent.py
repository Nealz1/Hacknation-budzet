from sqlalchemy.orm import Session
from typing import List, Dict, Tuple, Optional
from ..models import BudgetEntry, BudgetClassification
import json
import re

class ComplianceAgent:
    
    PARAGRAF_CLASSIFICATIONS = {
        6010: {"name": "Wydatki na zakup i objęcie akcji i udziałów", "group": "investment"},
        6020: {"name": "Wydatki na wniesienie wkładów do spółek prawa handlowego", "group": "investment"},
        6050: {"name": "Wydatki inwestycyjne jednostek budżetowych", "group": "investment"},
        6060: {"name": "Wydatki na zakupy inwestycyjne jednostek budżetowych", "group": "investment"},
        6070: {"name": "Wydatki inwestycyjne samorządowych zakładów budżetowych", "group": "investment"},
        
        4010: {"name": "Wynagrodzenia osobowe pracowników", "group": "current", "keywords": ["wynagrodzenia", "pensje", "pracownik"]},
        4110: {"name": "Składki na ubezpieczenia społeczne", "group": "current"},
        4120: {"name": "Składki na Fundusz Pracy", "group": "current"},
        4170: {"name": "Wynagrodzenia bezosobowe", "group": "current", "keywords": ["umowy zlecenia", "umowy o dzieło"]},
        4210: {"name": "Zakup materiałów i wyposażenia", "group": "current", "keywords": ["materiały biurowe", "artykuły"]},
        4260: {"name": "Zakup energii", "group": "current"},
        4270: {"name": "Zakup usług remontowych", "group": "current", "keywords": ["remont", "naprawa"]},
        4300: {"name": "Zakup usług pozostałych", "group": "current", "keywords": ["usługi", "serwis"]},
        4360: {"name": "Opłaty z tytułu zakupu usług telekomunikacyjnych", "group": "current"},
        4390: {"name": "Zakup usług obejmujących wykonanie ekspertyz", "group": "current", "keywords": ["ekspertyza", "analiza", "audyt"]},
        4400: {"name": "Opłaty za administrowanie i czynsze", "group": "current"},
        4410: {"name": "Podróże służbowe krajowe", "group": "current"},
        4420: {"name": "Podróże służbowe zagraniczne", "group": "current"},
        4430: {"name": "Różne opłaty i składki", "group": "current"},
        4440: {"name": "Odpisy na zakładowy fundusz świadczeń socjalnych", "group": "current"},
        4480: {"name": "Podatek od nieruchomości", "group": "current"},
        4520: {"name": "Opłaty na rzecz budżetów jednostek samorządu terytorialnego", "group": "current"},
        4610: {"name": "Koszty postępowania sądowego", "group": "current"},
        
        2570: {"name": "Dotacja podmiotowa z budżetu dla pozostałych jednostek", "group": "subsidy"},
        2580: {"name": "Dotacja podmiotowa z budżetu dla jednostek niezaliczanych do sektora finansów publicznych", "group": "subsidy"},
    }
    
    INVESTMENT_KEYWORDS = [
        "serwer", "server", "sprzęt komputerowy", "hardware", 
        "zakup sprzętu", "infrastruktura", "modernizacja",
        "budowa", "rozbudowa", "urządzenia sieciowe",
        "switch", "router", "firewall", "macierz"
    ]
    
    CURRENT_KEYWORDS = [
        "licencja", "license", "oprogramowanie", "software",
        "subskrypcja", "subscription", "szkolenie", "training",
        "usługa", "serwis", "support", "utrzymanie"
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self.validation_log = []
    
    def validate_entry(self, entry: BudgetEntry) -> Dict:
        result = {
            "is_valid": True,
            "warnings": [],
            "auto_corrections": [],
            "suggested_paragraf": None,
            "compliance_score": 100
        }
        
        if entry.paragraf:
            paragraf_check = self._validate_paragraf(entry)
            result["warnings"].extend(paragraf_check["warnings"])
            if paragraf_check["suggested_paragraf"]:
                result["suggested_paragraf"] = paragraf_check["suggested_paragraf"]
                result["auto_corrections"].append({
                    "field": "paragraf",
                    "original": entry.paragraf,
                    "corrected": paragraf_check["suggested_paragraf"],
                    "reason": paragraf_check["reason"]
                })
                result["compliance_score"] -= 20
        
        classification_check = self._validate_classification(entry)
        result["warnings"].extend(classification_check["warnings"])
        if classification_check["auto_corrections"]:
            result["auto_corrections"].extend(classification_check["auto_corrections"])
            result["compliance_score"] -= 15
        
        amount_check = self._validate_amounts(entry)
        result["warnings"].extend(amount_check["warnings"])
        if amount_check["warnings"]:
            result["compliance_score"] -= 10
        
        field_check = self._validate_required_fields(entry)
        result["warnings"].extend(field_check["warnings"])
        if field_check["warnings"]:
            result["compliance_score"] -= 5 * len(field_check["warnings"])
        
        result["is_valid"] = result["compliance_score"] >= 70
        result["compliance_score"] = max(0, result["compliance_score"])
        
        return result
    
    def _validate_paragraf(self, entry: BudgetEntry) -> Dict:
        result = {"warnings": [], "suggested_paragraf": None, "reason": None}
        
        if not entry.paragraf:
            result["warnings"].append("⚠️ Brak paragrafu - wymagane jest przypisanie paragrafu klasyfikacji budżetowej")
            return result
        
        if entry.paragraf not in self.PARAGRAF_CLASSIFICATIONS:
            result["warnings"].append(
                f"⚠️ Nieznany paragraf {entry.paragraf} - sprawdź zgodność z Rozporządzeniem MF"
            )
        else:
            paragraf_info = self.PARAGRAF_CLASSIFICATIONS[entry.paragraf]
            content = self._get_entry_content(entry)
            
            if paragraf_info["group"] == "current":
                for keyword in self.INVESTMENT_KEYWORDS:
                    if keyword in content:
                        result["warnings"].append(
                            f"⚠️ Ostrzeżenie o zgodności: Zgodnie z Rozporządzeniem 2c, "
                            f"zakup '{keyword}' kwalifikuje się jako 'Zakupy inwestycyjne' (Paragraf 6060), "
                            f"a nie '{paragraf_info['name']}' (Paragraf {entry.paragraf})"
                        )
                        result["suggested_paragraf"] = 6060
                        result["reason"] = f"Wykryto słowo kluczowe '{keyword}' wskazujące na zakup inwestycyjny"
                        break
            
            if paragraf_info["group"] == "investment":
                for keyword in self.CURRENT_KEYWORDS:
                    if keyword in content:
                        result["warnings"].append(
                            f"⚠️ Ostrzeżenie: '{keyword}' może wymagać klasyfikacji jako wydatek bieżący, "
                            f"nie inwestycyjny (rozważ paragraf 4300 lub 4210)"
                        )
                        break
        
        return result
    
    def _validate_classification(self, entry: BudgetEntry) -> Dict:
        result = {"warnings": [], "auto_corrections": []}
        
        if not entry.paragraf:
            return result
        
        if entry.beneficjent_zadaniowy:
            bz = entry.beneficjent_zadaniowy
            bz_pattern = r'^\d+\.\d+\.\d+\.\d+\.?$'
            if not re.match(bz_pattern, str(bz)):
                if bz != '0' and bz.lower() not in ['nd', 'n/d', 'nan', '']:
                    result["warnings"].append(
                        f"⚠️ Format kodu BZ '{bz}' może być nieprawidłowy. "
                        f"Oczekiwany format: XX.X.X.X (np. 16.1.2.1)"
                    )
        
        return result
    
    def _validate_amounts(self, entry: BudgetEntry) -> Dict:
        result = {"warnings": []}
        
        amounts = [
            entry.kwota_2025 or 0,
            entry.kwota_2026 or 0,
            entry.kwota_2027 or 0,
            entry.kwota_2028 or 0,
            entry.kwota_2029 or 0
        ]
        
        max_amount = max(amounts)
        if max_amount > 50000:
            result["warnings"].append(
                f"⚠️ Wysokie jednorazowe wydatki ({max_amount:,.0f} tys. PLN) - "
                f"wymaga zatwierdzenia przez Kierownictwo"
            )
        
        if entry.is_obligatory and amounts[0] > 0:
            if amounts[1] < amounts[0] * 0.5:
                result["warnings"].append(
                    f"⚠️ Zadanie obligatoryjne wykazuje znaczący spadek finansowania w 2026 "
                    f"- sprawdź poprawność danych"
                )
        
        if entry.paragraf and entry.paragraf >= 6000:
            if amounts[0] > 1000 and all(a == 0 for a in amounts[1:]):
                result["warnings"].append(
                    f"⚠️ Inwestycja bez planowania wieloletniego - rozważ rozłożenie wydatków"
                )
        
        return result
    
    def _validate_required_fields(self, entry: BudgetEntry) -> Dict:
        result = {"warnings": []}
        
        if not entry.nazwa_zadania and not entry.opis_projektu:
            result["warnings"].append("⚠️ Brak nazwy zadania lub opisu projektu")
        
        if not entry.department_id:
            result["warnings"].append("⚠️ Brak przypisania do departamentu")
        
        if entry.paragraf and entry.paragraf >= 6000:
            if not entry.zadanie_inwestycyjne:
                result["warnings"].append(
                    "⚠️ Wydatek inwestycyjny wymaga wskazania zadania inwestycyjnego"
                )
        
        return result
    
    def _get_entry_content(self, entry: BudgetEntry) -> str:
        fields = [
            entry.nazwa_zadania or '',
            entry.opis_projektu or '',
            entry.szczegolowe_uzasadnienie or '',
            entry.zadanie_inwestycyjne or '',
            entry.uwagi or ''
        ]
        return ' '.join(fields).lower()
    
    def validate_all_entries(self) -> List[Dict]:
        entries = self.db.query(BudgetEntry).all()
        results = []
        
        for entry in entries:
            validation = self.validate_entry(entry)
            
            entry.compliance_validated = True
            entry.compliance_warnings = json.dumps(validation["warnings"], ensure_ascii=False)
            
            if validation["suggested_paragraf"] and entry.paragraf != validation["suggested_paragraf"]:
                entry.original_paragraf = entry.paragraf
            
            results.append({
                "entry_id": entry.id,
                "nazwa": entry.nazwa_zadania or entry.opis_projektu,
                "validation": validation
            })
        
        self.db.commit()
        return results
    
    def get_compliance_summary(self) -> Dict:
        entries = self.db.query(BudgetEntry).all()
        
        total = len(entries)
        validated = sum(1 for e in entries if e.compliance_validated)
        with_warnings = sum(1 for e in entries if e.compliance_warnings and e.compliance_warnings != '[]')
        
        return {
            "total_entries": total,
            "validated": validated,
            "with_warnings": with_warnings,
            "compliance_rate": (total - with_warnings) / total * 100 if total > 0 else 100
        }
