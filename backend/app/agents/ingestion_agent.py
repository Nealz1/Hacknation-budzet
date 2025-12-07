import pandas as pd
from sqlalchemy.orm import Session
from typing import Optional
from ..models import BudgetEntry, Department, BudgetClassification, GlobalLimit, PriorityLevel, BudgetStatus
from ..database import SessionLocal, init_db
import os
import json

class IngestionAgent:
    
    COLUMN_MAPPING = {
        'część': 'czesc',
        'departament': 'department_code',
        'rodzaj projektu': 'rodzaj_projektu',
        'opis projektu': 'opis_projektu',
        'DATA ZŁOŻENIA WNIOSKU/\nPLANOWANA DATA ZŁOŻENIA WNIOSKU / PREUMOWA': 'data_zlozenia',
        'PROGRAM OPERACYJNY/ INICJATYWA': 'program_operacyjny',
        'termin realizacji\n': 'termin_realizacji',
        'paragraf': 'paragraf',
        'źródło fin.': 'zrodlo_finansowania',
        'bz': 'beneficjent_zadaniowy',
        'Beneficjent': 'beneficjent',
        'nazwa zadania\n': 'nazwa_zadania',
        'Szczegółowe uzasadnienie': 'szczegolowe_uzasadnienie',
        2025.0: 'kwota_2025',
        2026.0: 'kwota_2026',
        2027.0: 'kwota_2027',
        2028.0: 'kwota_2028',
        2029.0: 'kwota_2029',
        'etap działań': 'etap_dzialan',
        'umowy': 'umowy',
        'nr umowy': 'nr_umowy',
        'z kim zawarta': 'z_kim_zawarta',
        'Uwagi': 'uwagi',
        'zadanie inwestycyjne': 'zadanie_inwestycyjne'
    }
    
    DEFAULT_DEPARTMENTS = [
        {'code': 'DTC', 'name': 'Departament Transformacji Cyfrowej'},
        {'code': 'BA', 'name': 'Biuro Administracyjne'},
        {'code': 'BBF', 'name': 'Biuro Budżetowo-Finansowe'},
        {'code': 'DK', 'name': 'Departament Komunikacji'},
        {'code': 'DPK', 'name': 'Departament Prawny i Kontroli'},
        {'code': 'DC', 'name': 'Departament Cyberbezpieczeństwa'},
        {'code': 'DI', 'name': 'Departament Infrastruktury'},
        {'code': 'DSI', 'name': 'Departament Systemów Informatycznych'},
        {'code': 'DZ', 'name': 'Departament Zarządzania'},
        {'code': 'BK', 'name': 'Biuro Kadr'},
        {'code': 'BZP', 'name': 'Biuro Zamówień Publicznych'},
        {'code': 'BR', 'name': 'Biuro Rozliczeń'},
        {'code': 'BDG', 'name': 'Biuro Dyrektora Generalnego'},
        {'code': 'BSK', 'name': 'Biuro Spraw Kierownictwa'},
        {'code': 'BKI', 'name': 'Biuro Koordynacji Inwestycji'},
        {'code': 'UNKNOWN', 'name': 'Nieprzypisany'},
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self.department_cache = {}
        self.ingestion_log = []
    
    def setup_departments(self):
        for dept_data in self.DEFAULT_DEPARTMENTS:
            existing = self.db.query(Department).filter(
                Department.code == dept_data['code']
            ).first()
            
            if not existing:
                dept = Department(
                    code=dept_data['code'],
                    name=dept_data['name'],
                    budget_limit=0
                )
                self.db.add(dept)
        
        self.db.commit()
        
        departments = self.db.query(Department).all()
        self.department_cache = {d.code: d.id for d in departments}
        
        return len(self.DEFAULT_DEPARTMENTS)
    
    def setup_global_limit(self, year: int = 2025, limit: float = 100000000):
        existing = self.db.query(GlobalLimit).filter(GlobalLimit.year == year).first()
        
        if existing:
            existing.total_limit = limit
        else:
            global_limit = GlobalLimit(year=year, total_limit=limit)
            self.db.add(global_limit)
        
        self.db.commit()
    
    def ingest_excel(self, file_path: str) -> dict:
        results = {
            'success': True,
            'entries_processed': 0,
            'entries_created': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            df = pd.read_excel(file_path, header=0)
            
            df.columns = df.columns.str.strip() if hasattr(df.columns.str, 'strip') else df.columns
            
            results['entries_processed'] = len(df)
            
            for idx, row in df.iterrows():
                try:
                    entry = self._process_row(row, idx)
                    if entry:
                        self.db.add(entry)
                        results['entries_created'] += 1
                except Exception as e:
                    results['warnings'].append(f"Row {idx}: {str(e)}")
            
            self.db.commit()
            
            self._update_totals()
            
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            self.db.rollback()
        
        return results
    
    def _process_row(self, row, idx: int) -> Optional[BudgetEntry]:
        
        dept_code = self._safe_get(row, 'departament', 'UNKNOWN')
        if dept_code not in self.department_cache:
            dept_code = 'UNKNOWN'
        
        dept_id = self.department_cache.get(dept_code, self.department_cache.get('UNKNOWN'))
        
        kwota_2025 = self._parse_float(row.get('2025', row.get(2025.0, row.get(2025, 0))))
        kwota_2026 = self._parse_float(row.get('2026', row.get(2026.0, row.get(2026, 0))))
        kwota_2027 = self._parse_float(row.get('2027', row.get(2027.0, row.get(2027, 0))))
        kwota_2028 = self._parse_float(row.get('2028', row.get(2028.0, row.get(2028, 0))))
        kwota_2029 = self._parse_float(row.get('2029', row.get(2029.0, row.get(2029, 0))))
        
        if kwota_2025 == 0 and kwota_2026 == 0 and kwota_2027 == 0:
            if not self._safe_get(row, 'nazwa zadania\n') and not self._safe_get(row, 'opis projektu'):
                return None
        
        priority = self._determine_priority(row)
        
        entry = BudgetEntry(
            czesc=self._parse_int(row.get('część', 27)),
            department_id=dept_id,
            paragraf=self._parse_int(row.get('paragraf')),
            zrodlo_finansowania=str(row.get('źródło fin.', '0'))[:10] if pd.notna(row.get('źródło fin.')) else '0',
            beneficjent_zadaniowy=self._safe_get(row, 'bz'),
            
            rodzaj_projektu=self._safe_get(row, 'rodzaj projektu'),
            opis_projektu=self._safe_get(row, 'opis projektu'),
            nazwa_zadania=self._safe_get(row, 'nazwa zadania\n'),
            szczegolowe_uzasadnienie=self._safe_get(row, 'Szczegółowe uzasadnienie'),
            
            kwota_2025=kwota_2025,
            kwota_2026=kwota_2026,
            kwota_2027=kwota_2027,
            kwota_2028=kwota_2028,
            kwota_2029=kwota_2029,
            
            priority=priority,
            is_obligatory=(priority == 'obligatory'),
            status='draft',
            
            etap_dzialan=self._safe_get(row, 'etap działań'),
            umowy=self._safe_get(row, 'umowy'),
            nr_umowy=self._safe_get(row, 'nr umowy'),
            z_kim_zawarta=self._safe_get(row, 'z kim zawarta'),
            
            uwagi=self._safe_get(row, 'Uwagi'),
            zadanie_inwestycyjne=self._safe_get(row, 'zadanie inwestycyjne'),
            
            compliance_validated=False
        )
        
        return entry
    
    def _determine_priority(self, row) -> str:
        obligatory_keywords = [
            'obowiązkowe', 'obligatoryjne', 'prawne', 'ustawa', 
            'cyberbezpieczeństwo', 'audit', 'audyt', 'kontrola',
            'eidas', 'rozporządzenie'
        ]
        
        discretionary_keywords = [
            'planowane', 'opcjonalne', 'nowe', 'rozwój'
        ]
        
        text_fields = [
            str(row.get('nazwa zadania\n', '')).lower(),
            str(row.get('opis projektu', '')).lower(),
            str(row.get('Szczegółowe uzasadnienie', '')).lower(),
            str(row.get('etap działań', '')).lower()
        ]
        
        combined_text = ' '.join(text_fields)
        
        for keyword in obligatory_keywords:
            if keyword in combined_text:
                return 'obligatory'
        
        for keyword in discretionary_keywords:
            if keyword in combined_text:
                return 'discretionary'
        
        amount = self._parse_float(row.get('2025', row.get(2025.0, row.get(2025, 0))))
        if amount > 10000:
            return 'high'
        elif amount > 1000:
            return 'medium'
        
        return 'low'
    
    def _safe_get(self, row, key, default=''):
        val = row.get(key, default)
        if pd.isna(val):
            return default
        return str(val)[:500] if val else default
    
    def _parse_float(self, val) -> float:
        if pd.isna(val):
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
    
    def _parse_int(self, val) -> Optional[int]:
        if pd.isna(val):
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None
    
    def _update_totals(self):
        total_2025 = self.db.query(BudgetEntry).with_entities(
            BudgetEntry.kwota_2025
        ).all()
        
        total = sum(t[0] or 0 for t in total_2025)
        
        global_limit = self.db.query(GlobalLimit).filter(GlobalLimit.year == 2025).first()
        if global_limit:
            global_limit.current_total = total
            global_limit.variance = total - global_limit.total_limit
            self.db.commit()

def run_ingestion(excel_path: str = None):
    init_db()
    
    db = SessionLocal()
    try:
        agent = IngestionAgent(db)
        
        dept_count = agent.setup_departments()
        print(f"✅ Initialized {dept_count} departments")
        
        agent.setup_global_limit(2025, 100000)
        print(f"✅ Set global limit for 2025")
        
        if excel_path and os.path.exists(excel_path):
            results = agent.ingest_excel(excel_path)
            print(f"✅ Ingestion complete:")
            print(f"   - Processed: {results['entries_processed']} rows")
            print(f"   - Created: {results['entries_created']} entries")
            if results['warnings']:
                print(f"   - Warnings: {len(results['warnings'])}")
            return results
        else:
            print("⚠️ No Excel file provided or file not found")
            return {'success': True, 'message': 'Setup complete, no data ingested'}
    
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    excel_path = sys.argv[1] if len(sys.argv) > 1 else None
    run_ingestion(excel_path)
