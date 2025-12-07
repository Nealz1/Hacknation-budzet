from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
import math

from ..models import BudgetEntry, Department, GlobalLimit, PriorityLevel

@dataclass
class ForecastResult:
    year: int
    predicted_total: float
    confidence: float
    breakdown: Dict[str, float]
    trend: str
    risk_factors: List[str]

class ForecasterAgent:
    
    def __init__(self, db: Session):
        self.db = db
        
        self.growth_factors = {
            "cybersecurity": 1.15,
            "digital_transformation": 1.20,
            "maintenance": 1.02,
            "contracts": 1.0,
            "staff": 1.03
        }
        
        self.category_keywords = {
            "cybersecurity": ["cyber", "bezpieczeństwo", "CSIRT", "security", "SOC"],
            "digital_transformation": ["transformacja", "cyfryzacja", "digitalizacja", "eIDAS"],
            "maintenance": ["utrzymanie", "maintenance", "bieżące", "eksploatacja"],
            "contracts": ["umowa", "contract", "COI", "realizacja"],
            "staff": ["wynagrodzenia", "personal", "kadry", "ZUS"]
        }
    
    def forecast_budget(self, base_year: int = 2025, 
                       forecast_years: int = 3) -> Dict[str, Any]:
        
        forecasts = []
        base_data = self._get_year_data(base_year)
        
        for offset in range(1, forecast_years + 1):
            year = base_year + offset
            forecast = self._forecast_year(base_data, year, offset)
            forecasts.append(forecast)
        
        trend = self._analyze_trend(forecasts)
        
        return {
            "base_year": base_year,
            "base_total": base_data["total"],
            "forecasts": [self._forecast_to_dict(f) for f in forecasts],
            "trend_analysis": trend,
            "recommendations": self._generate_recommendations(base_data, forecasts),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _get_year_data(self, year: int) -> Dict:
        
        amount_field = getattr(BudgetEntry, f"kwota_{year}")
        entries = self.db.query(BudgetEntry).filter(amount_field > 0).all()
        
        categorized = {}
        for cat in self.category_keywords.keys():
            categorized[cat] = 0
        categorized["other"] = 0
        
        by_department = {}
        
        for entry in entries:
            amount = getattr(entry, f"kwota_{year}") or 0
            
            category = self._categorize_entry(entry)
            categorized[category] += amount
            
            dept_code = entry.department.code if entry.department else "UNKNOWN"
            by_department[dept_code] = by_department.get(dept_code, 0) + amount
        
        return {
            "year": year,
            "total": sum(getattr(e, f"kwota_{year}") or 0 for e in entries),
            "entries_count": len(entries),
            "by_category": categorized,
            "by_department": by_department,
            "obligatory_total": sum(getattr(e, f"kwota_{year}") or 0 for e in entries if e.is_obligatory),
            "entries": entries
        }
    
    def _categorize_entry(self, entry: BudgetEntry) -> str:
        
        text = " ".join([
            entry.nazwa_zadania or "",
            entry.opis_projektu or "",
            entry.szczegolowe_uzasadnienie or ""
        ]).lower()
        
        for category, keywords in self.category_keywords.items():
            if any(kw.lower() in text for kw in keywords):
                return category
        
        return "other"
    
    def _forecast_year(self, base_data: Dict, year: int, offset: int) -> ForecastResult:
        
        predicted_by_category = {}
        risk_factors = []
        
        for category, base_amount in base_data["by_category"].items():
            growth = self.growth_factors.get(category, 1.03)
            
            predicted = base_amount * (growth ** offset)
            predicted_by_category[category] = predicted
            
            if category == "cybersecurity" and offset >= 2:
                risk_factors.append(f"Cyberbezpieczeństwo: szybki wzrost (+{(growth**offset-1)*100:.0f}%)")
        
        total_predicted = sum(predicted_by_category.values())
        
        confidence = max(0.5, 1 - (offset * 0.15))
        
        if total_predicted > base_data["total"] * 1.1:
            trend = "increasing"
        elif total_predicted < base_data["total"] * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
        
        dept_breakdown = {}
        base_ratio = base_data["by_department"]
        total_base = base_data["total"]
        
        for dept_code, dept_amount in base_ratio.items():
            if total_base > 0:
                ratio = dept_amount / total_base
                dept_breakdown[dept_code] = total_predicted * ratio
            else:
                dept_breakdown[dept_code] = 0
        
        return ForecastResult(
            year=year,
            predicted_total=total_predicted,
            confidence=confidence,
            breakdown=dept_breakdown,
            trend=trend,
            risk_factors=risk_factors
        )
    
    def _forecast_to_dict(self, forecast: ForecastResult) -> Dict:
        return {
            "year": forecast.year,
            "predicted_total": round(forecast.predicted_total, 0),
            "confidence": round(forecast.confidence, 2),
            "trend": forecast.trend,
            "department_breakdown": {k: round(v, 0) for k, v in forecast.breakdown.items()},
            "risk_factors": forecast.risk_factors
        }
    
    def _analyze_trend(self, forecasts: List[ForecastResult]) -> Dict:
        
        if not forecasts:
            return {"trend": "unknown", "growth_rate": 0}
        
        first = forecasts[0].predicted_total
        last = forecasts[-1].predicted_total if len(forecasts) > 1 else first
        
        total_growth = ((last / first) - 1) * 100 if first > 0 else 0
        annual_growth = total_growth / len(forecasts) if forecasts else 0
        
        if annual_growth > 10:
            trend = "rapidly_increasing"
            warning = "⚠️ Szybki wzrost wydatków - wymaga uwagi"
        elif annual_growth > 5:
            trend = "increasing"
            warning = None
        elif annual_growth > -5:
            trend = "stable"
            warning = None
        else:
            trend = "decreasing"
            warning = "📉 Spadek wydatków - sprawdź czy nie pominięto zadań"
        
        return {
            "trend": trend,
            "total_growth_percent": round(total_growth, 1),
            "annual_growth_percent": round(annual_growth, 1),
            "warning": warning
        }
    
    def _generate_recommendations(self, base_data: Dict, 
                                  forecasts: List[ForecastResult]) -> List[Dict]:
        
        recommendations = []
        
        if forecasts:
            last_forecast = forecasts[-1]
            if last_forecast.predicted_total > base_data["total"] * 1.5:
                recommendations.append({
                    "priority": "high",
                    "type": "budget_growth",
                    "title": "Szybki wzrost wydatków",
                    "description": f"Prognozowany budżet na {last_forecast.year} to {last_forecast.predicted_total:,.0f} tys. PLN (wzrost o {((last_forecast.predicted_total/base_data['total'])-1)*100:.0f}%)",
                    "action": "Rozpocznij negocjacje z MF w sprawie zwiększenia limitu lub zidentyfikuj potencjalne cięcia"
                })
        
        cyber_base = base_data["by_category"].get("cybersecurity", 0)
        if cyber_base > base_data["total"] * 0.3:
            recommendations.append({
                "priority": "średni",
                "type": "category_concentration",
                "title": "Koncentracja w cyberbezpieczeństwie",
                "description": f"Cyberbezpieczeństwo stanowi {(cyber_base/base_data['total'])*100:.0f}% budżetu",
                "action": "Rozważ konsolidację zamówień lub współdzielenie zasobów z innymi jednostkami"
            })
        
        oblig_ratio = base_data["obligatory_total"] / base_data["total"] if base_data["total"] > 0 else 0
        if oblig_ratio > 0.7:
            recommendations.append({
                "priority": "high",
                "type": "flexibility",
                "title": "Niska elastyczność budżetu",
                "description": f"{oblig_ratio*100:.0f}% wydatków to zadania obligatoryjne",
                "action": "W przypadku cięć budżetowych, mało miejsca na negocjacje"
            })
        
        return recommendations
    
    def detect_anomalies(self, year: int = 2025) -> List[Dict]:
        
        anomalies = []
        
        amount_field = getattr(BudgetEntry, f"kwota_{year}")
        entries = self.db.query(BudgetEntry).filter(amount_field > 0).all()
        
        if not entries:
            return []
        
        amounts = [getattr(e, f"kwota_{year}") or 0 for e in entries]
        mean = sum(amounts) / len(amounts)
        variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
        std_dev = math.sqrt(variance) if variance > 0 else 1
        
        for entry in entries:
            amount = getattr(entry, f"kwota_{year}") or 0
            z_score = (amount - mean) / std_dev if std_dev > 0 else 0
            
            if abs(z_score) > 3:
                anomalies.append({
                    "type": "outlier",
                    "severity": "high" if z_score > 4 else "medium",
                    "entry_id": entry.id,
                    "description": f"Kwota {amount:,.0f} jest {z_score:.1f}σ od średniej",
                    "task": entry.nazwa_zadania or entry.opis_projektu,
                    "recommendation": "Zweryfikuj poprawność danych"
                })
            
            if amount > 10000 and not entry.szczegolowe_uzasadnienie:
                anomalies.append({
                    "type": "missing_justification",
                    "severity": "medium",
                    "entry_id": entry.id,
                    "description": f"Brak uzasadnienia dla kwoty {amount:,.0f} tys. PLN",
                    "task": entry.nazwa_zadania or entry.opis_projektu,
                    "recommendation": "Uzupełnij szczegółowe uzasadnienie"
                })
            
            if entry.paragraf:
                is_investment = entry.paragraf >= 600 and entry.paragraf < 700
                text = (entry.nazwa_zadania or entry.opis_projektu or "").lower()
                
                investment_keywords = ["zakup", "budowa", "inwestycja", "sprzęt"]
                has_investment_keyword = any(kw in text for kw in investment_keywords)
                
                if is_investment and not has_investment_keyword:
                    anomalies.append({
                        "type": "classification_mismatch",
                        "severity": "low",
                        "entry_id": entry.id,
                        "description": f"Paragraf inwestycyjny ({entry.paragraf}) ale brak słów kluczowych inwestycyjnych",
                        "task": entry.nazwa_zadania or entry.opis_projektu,
                        "recommendation": "Sprawdź poprawność klasyfikacji"
                    })
        
        return anomalies
    
    def optimize_multi_year_allocation(self, total_limit: Dict[int, float]) -> Dict:
        
        entries = self.db.query(BudgetEntry).all()
        
        deferrable = []
        non_deferrable = []
        
        for entry in entries:
            if entry.is_obligatory or entry.priority == PriorityLevel.OBOWIAZKOWY:
                non_deferrable.append(entry)
            else:
                deferrable.append(entry)
        
        allocation = {}
        
        for year, limit in total_limit.items():
            year_non_def = sum(getattr(e, f"kwota_{year}") or 0 for e in non_deferrable)
            remaining = limit - year_non_def
            
            year_def = sum(getattr(e, f"kwota_{year}") or 0 for e in deferrable)
            
            allocation[year] = {
                "limit": limit,
                "non_deferrable": year_non_def,
                "deferrable_requested": year_def,
                "deferrable_allocated": min(year_def, max(0, remaining)),
                "total_allocated": year_non_def + min(year_def, max(0, remaining)),
                "gap": max(0, year_non_def + year_def - limit),
                "surplus": max(0, remaining - year_def)
            }
        
        shifts = []
        years = sorted(total_limit.keys())
        
        for i, year in enumerate(years[:-1]):
            next_year = years[i + 1]
            
            if allocation[year]["gap"] > 0 and allocation[next_year]["surplus"] > 0:
                shift_amount = min(allocation[year]["gap"], allocation[next_year]["surplus"])
                shifts.append({
                    "from_year": year,
                    "to_year": next_year,
                    "amount": shift_amount,
                    "reason": f"Przesunięcie {shift_amount:,.0f} tys. PLN z {year} na {next_year} w celu wyrównania budżetu"
                })
        
        return {
            "allocation": allocation,
            "suggested_shifts": shifts,
            "summary": f"Zoptymalizowano alokację dla {len(total_limit)} lat budżetowych"
        }
