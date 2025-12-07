from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Tuple
from ..models import BudgetEntry, BudgetConflict, Department
import re
from difflib import SequenceMatcher

class ConflictAgent:
    
    CATEGORY_KEYWORDS = {
        "software_licenses": ["licencja", "license", "microsoft", "office", "oprogramowanie", "software", "subskrypcja"],
        "hardware": ["serwer", "server", "sprzęt", "hardware", "komputer", "laptop", "urządzenia"],
        "network": ["sieciowe", "network", "switch", "router", "firewall", "wifi", "lan", "wan"],
        "consulting": ["konsulting", "consulting", "doradztwo", "ekspertyza", "analiza", "audyt"],
        "training": ["szkolenie", "training", "kurs", "certyfikacja", "edukacja"],
        "maintenance": ["utrzymanie", "maintenance", "serwis", "support", "wsparcie"],
        "renovation": ["remont", "renovation", "modernizacja", "adaptacja"],
        "security": ["bezpieczeństwo", "security", "cyber", "ochrona", "monitoring"]
    }
    
    SIMILARITY_THRESHOLD = 0.6
    
    def __init__(self, db: Session):
        self.db = db
    
    def detect_conflicts(self, year: int = 2025) -> List[Dict]:
        amount_field = getattr(BudgetEntry, f"kwota_{year}")
        
        entries = self.db.query(BudgetEntry).filter(
            amount_field > 0
        ).all()
        
        conflicts = []
        processed_pairs = set()
        
        for i, entry_a in enumerate(entries):
            for entry_b in entries[i+1:]:
                if entry_a.department_id == entry_b.department_id:
                    continue
                
                pair_key = tuple(sorted([entry_a.id, entry_b.id]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                
                similarity = self._calculate_similarity(entry_a, entry_b)
                
                if similarity >= self.SIMILARITY_THRESHOLD:
                    conflict = self._create_conflict(entry_a, entry_b, similarity, year)
                    conflicts.append(conflict)
                    
                    self._save_conflict(entry_a.id, entry_b.id, similarity, conflict['conflict_type'])
        
        conflicts.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return conflicts
    
    def _calculate_similarity(self, entry_a: BudgetEntry, entry_b: BudgetEntry) -> float:
        
        content_a = self._normalize_content(entry_a)
        content_b = self._normalize_content(entry_b)
        
        string_sim = SequenceMatcher(None, content_a, content_b).ratio()
        
        category_sim = self._category_similarity(content_a, content_b)
        
        paragraf_sim = 1.0 if entry_a.paragraf == entry_b.paragraf else 0.0
        
        total_similarity = (
            string_sim * 0.4 +
            category_sim * 0.4 +
            paragraf_sim * 0.2
        )
        
        return total_similarity
    
    def _normalize_content(self, entry: BudgetEntry) -> str:
        fields = [
            entry.nazwa_zadania or '',
            entry.opis_projektu or '',
            entry.szczegolowe_uzasadnienie or ''
        ]
        content = ' '.join(fields).lower()
        
        content = re.sub(r'[^\w\s]', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _category_similarity(self, content_a: str, content_b: str) -> float:
        
        categories_a = set()
        categories_b = set()
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_a:
                    categories_a.add(category)
                if keyword in content_b:
                    categories_b.add(category)
        
        if not categories_a or not categories_b:
            return 0.0
        
        intersection = len(categories_a & categories_b)
        union = len(categories_a | categories_b)
        
        return intersection / union if union > 0 else 0.0
    
    def _create_conflict(self, entry_a: BudgetEntry, entry_b: BudgetEntry, 
                        similarity: float, year: int) -> Dict:
        
        amount_a = getattr(entry_a, f"kwota_{year}") or 0
        amount_b = getattr(entry_b, f"kwota_{year}") or 0
        
        if similarity >= 0.85:
            conflict_type = "duplicate"
            suggested_action = "Połącz pozycje w jedno wspólne zamówienie"
        elif similarity >= 0.7:
            conflict_type = "overlap"
            suggested_action = "Rozważ konsolidację pod jednym departamentem"
        else:
            conflict_type = "semantic_similar"
            suggested_action = "Sprawdź czy nie ma możliwości synergii"
        
        potential_savings = (amount_a + amount_b) * 0.15
        
        dept_a = entry_a.department.code if entry_a.department else "N/A"
        dept_b = entry_b.department.code if entry_b.department else "N/A"
        
        return {
            "entry_a_id": entry_a.id,
            "entry_a_name": (entry_a.nazwa_zadania or entry_a.opis_projektu or "")[:100],
            "entry_a_department": dept_a,
            "entry_a_amount": amount_a,
            
            "entry_b_id": entry_b.id,
            "entry_b_name": (entry_b.nazwa_zadania or entry_b.opis_projektu or "")[:100],
            "entry_b_department": dept_b,
            "entry_b_amount": amount_b,
            
            "similarity_score": round(similarity, 2),
            "conflict_type": conflict_type,
            "suggested_action": suggested_action,
            "potential_savings": round(potential_savings, 2),
            "combined_amount": amount_a + amount_b,
            
            "message": f"🔄 Wykryto podobieństwo: Dept {dept_a} i Dept {dept_b} " +
                      f"zgłosiły podobne potrzeby. Rozważ konsolidację dla oszczędności ~{potential_savings:,.0f} tys. PLN"
        }
    
    def _save_conflict(self, entry_a_id: int, entry_b_id: int, 
                       similarity: float, conflict_type: str):
        
        existing = self.db.query(BudgetConflict).filter(
            ((BudgetConflict.entry_a_id == entry_a_id) & (BudgetConflict.entry_b_id == entry_b_id)) |
            ((BudgetConflict.entry_a_id == entry_b_id) & (BudgetConflict.entry_b_id == entry_a_id))
        ).first()
        
        if existing:
            existing.similarity_score = similarity
            existing.conflict_type = conflict_type
        else:
            conflict = BudgetConflict(
                entry_a_id=entry_a_id,
                entry_b_id=entry_b_id,
                similarity_score=similarity,
                conflict_type=conflict_type,
                resolution_status="pending"
            )
            self.db.add(conflict)
        
        self.db.commit()
    
    def resolve_conflict(self, conflict_id: int, resolution: str, 
                        keep_entry_id: int = None, notes: str = None) -> Dict:
        conflict = self.db.query(BudgetConflict).filter(
            BudgetConflict.id == conflict_id
        ).first()
        
        if not conflict:
            return {"success": False, "error": "Nie znaleziono konfliktu"}
        
        if resolution == "consolidate":
            if not keep_entry_id:
                return {"success": False, "error": "Nie wskazano pozycji do zachowania"}
            
            remove_id = conflict.entry_b_id if keep_entry_id == conflict.entry_a_id else conflict.entry_a_id
            
            keep_entry = self.db.query(BudgetEntry).filter(BudgetEntry.id == keep_entry_id).first()
            remove_entry = self.db.query(BudgetEntry).filter(BudgetEntry.id == remove_id).first()
            
            if keep_entry and remove_entry:
                for year in range(2025, 2030):
                    field = f"kwota_{year}"
                    keep_amount = getattr(keep_entry, field) or 0
                    remove_amount = getattr(remove_entry, field) or 0
                    consolidated = (keep_amount + remove_amount) * 0.85
                    setattr(keep_entry, field, consolidated)
                
                keep_entry.uwagi = (keep_entry.uwagi or '') + f"\n[SKONSOLIDOWANO z pozycji {remove_id}]"
                
                remove_entry.kwota_2025 = 0
                remove_entry.kwota_2026 = 0
                remove_entry.kwota_2027 = 0
                remove_entry.uwagi = (remove_entry.uwagi or '') + f"\n[PRZENIESIONO do pozycji {keep_entry_id}]"
        
        elif resolution == "keep_both":
            pass
        
        conflict.resolution_status = "resolved"
        conflict.resolution_notes = notes or resolution
        self.db.commit()
        
        return {
            "success": True,
            "resolution": resolution,
            "message": f"Konflikt rozwiązany: {resolution}"
        }
    
    def get_conflict_summary(self) -> Dict:
        
        pending = self.db.query(BudgetConflict).filter(
            BudgetConflict.resolution_status == "pending"
        ).count()
        
        resolved = self.db.query(BudgetConflict).filter(
            BudgetConflict.resolution_status == "resolved"
        ).count()
        
        by_type = self.db.query(
            BudgetConflict.conflict_type,
            func.count(BudgetConflict.id)
        ).group_by(BudgetConflict.conflict_type).all()
        
        return {
            "total_conflicts": pending + resolved,
            "pending": pending,
            "resolved": resolved,
            "by_type": {t: c for t, c in by_type}
        }
