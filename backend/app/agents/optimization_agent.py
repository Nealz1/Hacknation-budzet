from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Tuple
from ..models import BudgetEntry, Department, GlobalLimit, PriorityLevel, BudgetStatus
import json

class OptimizationAgent:
    
    PRIORITY_WEIGHTS = {
        PriorityLevel.OBOWIAZKOWY: 100,
        PriorityLevel.WYSOKI: 75,
        PriorityLevel.SREDNI: 50,
        PriorityLevel.NISKI: 25,
        PriorityLevel.UZNANIOWY: 10
    }
    
    PROTECTED_KEYWORDS = [
        "cyberbezpieczeństwo", "cyber", "security", "bezpieczeństwo",
        "eidas", "rozporządzenie", "ustawa", "prawne", "obligatoryjne",
        "audit", "audyt", "kontrola", "nis2", "dora"
    ]
    
    DEFERRABLE_KEYWORDS = [
        "remont", "renovation", "modernizacja", "szkolenie", "training",
        "nowe", "rozwój", "enhancement", "upgrade", "planowane"
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_budget_gap(self, year: int = 2025) -> Dict:
        global_limit = self.db.query(GlobalLimit).filter(GlobalLimit.year == year).first()
        
        if not global_limit:
            return {"error": "Brak limitu globalnego dla roku " + str(year)}
        
        amount_field = getattr(BudgetEntry, f"kwota_{year}")
        current_total = self.db.query(func.sum(amount_field)).scalar() or 0
        
        priority_breakdown = {}
        for priority in PriorityLevel:
            total = self.db.query(func.sum(amount_field)).filter(
                BudgetEntry.priority == priority.value
            ).scalar() or 0
            priority_breakdown[priority.value] = total
        
        dept_breakdown = self.db.query(
            Department.code,
            func.sum(amount_field)
        ).join(BudgetEntry).group_by(Department.code).all()
        
        variance = current_total - global_limit.total_limit
        
        return {
            "year": year,
            "global_limit": global_limit.total_limit,
            "current_total": current_total,
            "variance": variance,
            "is_over_limit": variance > 0,
            "over_percentage": (variance / global_limit.total_limit * 100) if global_limit.total_limit > 0 else 0,
            "priority_breakdown": priority_breakdown,
            "department_breakdown": {code: amount for code, amount in dept_breakdown},
            "obowiązkowy_total": priority_breakdown.get('obowiązkowy', 0),
            "uznaniowy_total": priority_breakdown.get('uznaniowy', 0)
        }
    
    def generate_cut_suggestions(self, target_reduction: float = None, year: int = 2025) -> Dict:
        gap_analysis = self.analyze_budget_gap(year)
        
        if not gap_analysis.get('is_over_limit', False):
            return {
                "message": "Budżet mieści się w limicie - brak potrzeby cięć",
                "suggestions": [],
                "gap_analysis": gap_analysis
            }
        
        variance = gap_analysis['variance']
        target = target_reduction or variance
        
        amount_field = getattr(BudgetEntry, f"kwota_{year}")
        
        cuttable_entries = self.db.query(BudgetEntry).filter(
            BudgetEntry.is_obligatory == False,
            amount_field > 0
        ).order_by(
            BudgetEntry.priority.asc()
        ).all()
        
        suggestions = []
        cumulative_savings = 0
        
        for entry in cuttable_entries:
            if cumulative_savings >= target:
                break
            
            entry_amount = getattr(entry, f"kwota_{year}") or 0
            if entry_amount <= 0:
                continue
            
            score = self._calculate_deferral_score(entry)
            
            is_deferrable = self._is_deferrable(entry)
            
            if is_deferrable:
                action = "defer"
                suggested_amount = 0
                savings = entry_amount
                reason = f"Przełożenie na {year + 1} - zadanie nie jest krytyczne w roku {year}"
            else:
                reduction_rate = 0.3 if entry.priority in ['średni', 'niski'] else 0.2
                suggested_amount = entry_amount * (1 - reduction_rate)
                savings = entry_amount - suggested_amount
                action = "reduce"
                reason = f"Redukcja o {reduction_rate*100:.0f}% - zachowanie podstawowej funkcjonalności"
            
            suggestion = {
                "entry_id": entry.id,
                "nazwa": entry.nazwa_zadania or entry.opis_projektu or "Brak nazwy",
                "department": entry.department.code if entry.department else "N/A",
                "current_amount": entry_amount,
                "suggested_amount": suggested_amount,
                "savings": savings,
                "action": action,
                "reason": reason,
                "priority": entry.priority if entry.priority else "średni",
                "deferral_score": score,
                "is_deferrable": is_deferrable
            }
            
            suggestions.append(suggestion)
            cumulative_savings += savings
        
        suggestions.sort(key=lambda x: x["deferral_score"], reverse=True)
        
        summary = self._generate_summary(
            variance=variance,
            target=target,
            cumulative_savings=cumulative_savings,
            suggestions=suggestions
        )
        
        return {
            "gap_analysis": gap_analysis,
            "target_reduction": target,
            "achievable_reduction": cumulative_savings,
            "can_meet_target": cumulative_savings >= target,
            "suggestions": suggestions,
            "summary": summary,
            "protected_items": self._get_protected_items(year)
        }
    
    def _calculate_deferral_score(self, entry: BudgetEntry) -> float:
        priority_str = entry.priority if entry.priority else 'średni'
        try:
            score = 100 - self.PRIORITY_WEIGHTS.get(PriorityLevel(priority_str), 50)
        except ValueError:
            score = 50  # default for unknown priority
        
        content = self._get_entry_content(entry)
        
        for keyword in self.PROTECTED_KEYWORDS:
            if keyword in content:
                score -= 30
                break
        
        for keyword in self.DEFERRABLE_KEYWORDS:
            if keyword in content:
                score += 20
                break
        
        if entry.umowy and 'podpisana' in str(entry.umowy).lower():
            score -= 40
        
        if entry.etap_dzialan:
            stage = str(entry.etap_dzialan).lower()
            if 'realizacja' in stage or 'w toku' in stage:
                score -= 25
            elif 'planowane' in stage:
                score += 15
        
        return max(0, min(100, score))
    
    def _is_deferrable(self, entry: BudgetEntry) -> bool:
        
        if entry.umowy and 'podpisana' in str(entry.umowy).lower():
            return False
        
        if entry.etap_dzialan:
            stage = str(entry.etap_dzialan).lower()
            if 'realizacja' in stage or 'w toku' in stage:
                return False
        
        content = self._get_entry_content(entry)
        for keyword in self.PROTECTED_KEYWORDS:
            if keyword in content:
                return False
        
        return entry.priority in ['niski', 'uznaniowy']
    
    def _get_entry_content(self, entry: BudgetEntry) -> str:
        fields = [
            entry.nazwa_zadania or '',
            entry.opis_projektu or '',
            entry.szczegolowe_uzasadnienie or '',
            entry.uwagi or ''
        ]
        return ' '.join(fields).lower()
    
    def _generate_summary(self, variance: float, target: float, 
                         cumulative_savings: float, suggestions: List[Dict]) -> str:
        
        lines = []
        lines.append(f"📊 **Analiza Optymalizacji Budżetu**")
        lines.append(f"")
        lines.append(f"Przekroczenie limitu: **{variance:,.0f} tys. PLN**")
        lines.append(f"Cel redukcji: **{target:,.0f} tys. PLN**")
        lines.append(f"Możliwa redukcja: **{cumulative_savings:,.0f} tys. PLN**")
        lines.append(f"")
        
        if cumulative_savings >= target:
            lines.append(f"✅ Możliwe osiągnięcie celu redukcji")
        else:
            gap = target - cumulative_savings
            lines.append(f"⚠️ Brakuje {gap:,.0f} tys. PLN do osiągnięcia celu")
            lines.append(f"Wymagane decyzje Kierownictwa dot. zadań obligatoryjnych")
        
        lines.append(f"")
        lines.append(f"**Top 3 Sugestie:**")
        
        for i, s in enumerate(suggestions[:3], 1):
            action_pl = "Przełóż" if s["action"] == "defer" else "Zredukuj"
            lines.append(f"{i}. {action_pl} '{s['nazwa'][:50]}...' - oszczędność {s['savings']:,.0f} tys. PLN")
        
        return "\n".join(lines)
    
    def _get_protected_items(self, year: int = 2025) -> List[Dict]:
        amount_field = getattr(BudgetEntry, f"kwota_{year}")
        
        protected = self.db.query(BudgetEntry).filter(
            BudgetEntry.is_obligatory == True,
            amount_field > 0
        ).all()
        
        result = []
        for entry in protected:
            result.append({
                "entry_id": entry.id,
                "nazwa": entry.nazwa_zadania or entry.opis_projektu,
                "amount": getattr(entry, f"kwota_{year}"),
                "reason": "Zadanie obligatoryjne / wymóg prawny"
            })
        
        return result
    
    def apply_suggestion(self, entry_id: int, action: str, 
                        new_amount: float = None, year: int = 2025) -> Dict:
        entry = self.db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
        
        if not entry:
            return {"success": False, "error": "Nie znaleziono pozycji"}
        
        amount_field = f"kwota_{year}"
        old_amount = getattr(entry, amount_field)
        
        if action == "defer":
            setattr(entry, amount_field, 0)
            next_year_field = f"kwota_{year + 1}"
            current_next = getattr(entry, next_year_field, 0) or 0
            setattr(entry, next_year_field, current_next + old_amount)
            entry.uwagi = (entry.uwagi or '') + f"\n[ODROCZONO z {year}]"
        
        elif action == "reduce" and new_amount is not None:
            setattr(entry, amount_field, new_amount)
            entry.uwagi = (entry.uwagi or '') + f"\n[ZREDUKOWANO z {old_amount} do {new_amount}]"
        
        entry.status = 'needs_revision'
        self.db.commit()
        
        return {
            "success": True,
            "entry_id": entry_id,
            "action": action,
            "old_amount": old_amount,
            "new_amount": new_amount or 0,
            "message": f"Zastosowano {action} dla pozycji {entry_id}"
        }
    
    def get_department_allocation(self, year: int = 2025) -> List[Dict]:
        amount_field = getattr(BudgetEntry, f"kwota_{year}")
        
        results = self.db.query(
            Department.id,
            Department.code,
            Department.name,
            Department.budget_limit,
            func.sum(amount_field).label('total'),
            func.count(BudgetEntry.id).label('entry_count')
        ).join(
            BudgetEntry, Department.id == BudgetEntry.department_id
        ).group_by(Department.id).all()
        
        allocations = []
        for r in results:
            variance = (r.total or 0) - (r.budget_limit or 0)
            allocations.append({
                "department_id": r.id,
                "code": r.code,
                "name": r.name,
                "limit": r.budget_limit or 0,
                "total": r.total or 0,
                "entry_count": r.entry_count,
                "variance": variance,
                "is_over_limit": variance > 0,
                "status": "🔴 Przekroczenie" if variance > 0 else "🟢 W limicie"
            })
        
        return sorted(allocations, key=lambda x: x['variance'], reverse=True)
