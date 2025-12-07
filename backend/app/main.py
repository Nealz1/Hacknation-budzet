"""
Skarbnik AI - Agentic Budget Orchestration Platform
Main FastAPI Application
"""
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import os
import shutil
from datetime import datetime

from .database import get_db, init_db
from .models import BudgetEntry, Department, GlobalLimit, BudgetStatus, PriorityLevel, BudgetAuditLog
import json
from .schemas import (
    DepartmentCreate, DepartmentResponse,
    BudgetEntryCreate, BudgetEntryUpdate, BudgetEntryResponse,
    DashboardStats, AgentResponse, ComplianceCheck, BudgetOptimization
)
from .agents.ingestion_agent import IngestionAgent
from .agents.compliance_agent import ComplianceAgent
from .agents.semantic_compliance_agent import SemanticComplianceAgent
from .agents.optimization_agent import OptimizationAgent
from .agents.conflict_agent import ConflictAgent
from .agents.document_agent import DocumentAgent
from .agents.export_agent import ExportAgent
from .agents.orchestrator_agent import OrchestratorAgent
from .agents.forecaster_agent import ForecasterAgent

app = FastAPI(
    title="Skarbnik AI",
    description="Agentic Budget Orchestration Platform for Polish Public Finance",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount docs directory to serve PDF files
docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs")
if os.path.exists(docs_path):
    app.mount("/files", StaticFiles(directory=docs_path), name="docs")

# ============================================================================
# AUDIT LOGGING - Full Version History Tracking
# ============================================================================

def create_audit_log(
    db: Session,
    entry_id: int,
    action: str,
    old_values: dict = None,
    new_values: dict = None,
    user_id: str = "system",
    notes: str = None
):
    """Create an audit log entry for any budget change"""
    audit_entry = BudgetAuditLog(
        entry_id=entry_id,
        action=action,
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        user_id=user_id,
        notes=notes
    )
    db.add(audit_entry)
    db.commit()
    return audit_entry

def entry_to_dict(entry: BudgetEntry) -> dict:
    """Convert a budget entry to a dictionary for audit logging"""
    return {
        "id": entry.id,
        "czesc": entry.czesc,
        "paragraf": entry.paragraf,
        "department_id": entry.department_id,
        "nazwa_zadania": entry.nazwa_zadania,
        "opis_projektu": entry.opis_projektu,
        "kwota_2025": entry.kwota_2025,
        "kwota_2026": entry.kwota_2026,
        "kwota_2027": entry.kwota_2027,
        "kwota_2028": entry.kwota_2028,
        "kwota_2029": entry.kwota_2029,
        "priority": str(entry.priority) if entry.priority else None,
        "status": str(entry.status) if entry.status else None,
        "is_obligatory": entry.is_obligatory,
        "uwagi": entry.uwagi
    }


@app.get("/api/knowledge/files")
async def get_knowledge_files():
    """List all regulatory documents available to the AI"""
    files = []
    if os.path.exists(docs_path):
        for filename in sorted(os.listdir(docs_path)):
            if filename.endswith(".pdf") or filename.endswith(".xlsx"):
                stats = os.stat(os.path.join(docs_path, filename))
                files.append({
                    "name": filename,
                    "size": f"{stats.st_size / 1024:.1f} KB",
                    "type": "PDF" if filename.endswith(".pdf") else "EXCEL",
                    "url": f"http://localhost:8000/files/{filename}",
                    "status": "In Vector Store"
                })
    return files

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("🏛️ Skarbnik AI - Database initialized")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Skarbnik AI", "timestamp": datetime.utcnow()}

@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    
    total_entries = db.query(BudgetEntry).count()
    
    total_2025 = db.query(func.sum(BudgetEntry.kwota_2025)).scalar() or 0
    
    limit = db.query(GlobalLimit).filter(GlobalLimit.year == 2025).first()
    global_limit = limit.total_limit if limit else 0
    
    status_counts = db.query(
        BudgetEntry.status,
        func.count(BudgetEntry.id)
    ).group_by(BudgetEntry.status).all()
    
    dept_counts = db.query(
        Department.code,
        func.sum(BudgetEntry.kwota_2025)
    ).join(BudgetEntry).group_by(Department.code).all()
    
    obligatory = db.query(func.sum(BudgetEntry.kwota_2025)).filter(
        BudgetEntry.is_obligatory == True
    ).scalar() or 0
    
    discretionary = db.query(func.sum(BudgetEntry.kwota_2025)).filter(
        BudgetEntry.priority == PriorityLevel.DISCRETIONARY
    ).scalar() or 0
    
    return DashboardStats(
        total_entries=total_entries,
        total_budget_2025=total_2025,
        global_limit_2025=global_limit,
        variance=total_2025 - global_limit,
        entries_by_status={s if s else 'unknown': c for s, c in status_counts},
        entries_by_department={code: float(amount or 0) for code, amount in dept_counts},
        obligatory_total=obligatory,
        discretionary_total=discretionary
    )

@app.post("/api/ingest/excel")
async def ingest_excel_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and ingest Excel budget file"""
    
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        agent = IngestionAgent(db)
        agent.setup_departments()
        agent.setup_global_limit(2025, 100000)
        
        results = agent.ingest_excel(temp_path)
        
        return AgentResponse(
            agent_name="Ingestion Agent",
            action="ingest_excel",
            message=f"Successfully ingested {results['entries_created']} entries from {file.filename}",
            data=results,
            warnings=results.get('warnings', [])
        )
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/api/ingest/demo")
async def load_demo_data(db: Session = Depends(get_db)):
    """Load comprehensive demo data based on real Polish ministry budget patterns"""
    
    agent = IngestionAgent(db)
    agent.setup_departments()
    
    agent.setup_global_limit(2025, 100000)
    
    dept_limits = {
        'DTC': 50000,
        'DC': 25000,
        'DSI': 15000,
        'DK': 5000,
        'BA': 3000,
        'BBF': 2000,
    }
    
    for code, limit in dept_limits.items():
        dept = db.query(Department).filter(Department.code == code).first()
        if dept:
            dept.budget_limit = limit
    db.commit()
    
    demo_entries = [
        {'dept': 'DTC', 'paragraf': 6060, 'nazwa': 'Wdrożenie rozporządzenia eIDAS2',
         'opis': 'Implementacja europejskiego rozporządzenia o tożsamości cyfrowej',
         'kwota_2025': 13000, 'kwota_2026': 10000, 'kwota_2027': 10434,
         'priority': 'obowiązkowy', 'bz': '16.5.1.2', 'is_obligatory': True,
         'uzasadnienie': 'Obowiązek wynikający z Rozporządzenia PE i Rady (UE) 2024/1183'},
        
        {'dept': 'DTC', 'paragraf': 6060, 'nazwa': 'Umowa z COI - realizacja zadań Ministra',
         'opis': 'Umowa na realizację przez COI niektórych zadań Ministra Cyfryzacji',
         'kwota_2025': 45000, 'kwota_2026': 47000, 'kwota_2027': 49000,
         'priority': 'wysoki', 'bz': '16.1.2.1', 'contract': 'COI/2024/001'},
        
        {'dept': 'DTC', 'paragraf': 6060, 'nazwa': 'Rozbudowa systemu Dane.gov.pl',
         'opis': 'Rozbudowa Centralnego Repozytorium Danych Publicznych',
         'kwota_2025': 3090, 'kwota_2026': 2500, 'kwota_2027': 2000,
         'priority': 'średni', 'bz': '16.1.2.1'},
        
        {'dept': 'DTC', 'paragraf': 6060, 'nazwa': 'System dokumentacji prawnej',
         'opis': 'Budowa systemu dokumentacji prawnej dla administracji',
         'kwota_2025': 11933, 'kwota_2026': 5000, 'kwota_2027': 2000,
         'priority': 'średni', 'bz': '16.1.2.1'},
        
        {'dept': 'DTC', 'paragraf': 4300, 'nazwa': 'Zakup licencji ZPA',
         'opis': 'Licencje oprogramowania dla Zintegrowanej Platformy Analitycznej',
         'kwota_2025': 2500, 'kwota_2026': 2600, 'kwota_2027': 2700,
         'priority': 'wysoki', 'bz': '16.3.1.1'},
        
        {'dept': 'DC', 'paragraf': 4210, 'nazwa': 'Utrzymanie CSIRT GOV',
         'opis': 'Centrum Reagowania na Incydenty Cyberbezpieczeństwa',
         'kwota_2025': 15000, 'kwota_2026': 16500, 'kwota_2027': 18000,
         'priority': 'obowiązkowy', 'bz': '16.2.1.1', 'is_obligatory': True,
         'uzasadnienie': 'Obowiązek z art. 26 ustawy o krajowym systemie cyberbezpieczeństwa'},
        
        {'dept': 'DC', 'paragraf': 4300, 'nazwa': 'Rozbudowa SOC Ministerstwa',
         'opis': 'Security Operations Center - monitoring 24/7',
         'kwota_2025': 8000, 'kwota_2026': 8500, 'kwota_2027': 9000,
         'priority': 'wysoki', 'bz': '16.2.1.2'},
        
        {'dept': 'DC', 'paragraf': 6060, 'nazwa': 'Ochrona przed atakami DDoS',
         'opis': 'Dostawa urządzeń DefensePro z licencjami',
         'kwota_2025': 8904, 'kwota_2026': 1000, 'kwota_2027': 1000,
         'priority': 'wysoki', 'bz': '16.2.1.1'},
        
        {'dept': 'DC', 'paragraf': 4300, 'nazwa': 'Audyty bezpieczeństwa systemów',
         'opis': 'Zewnętrzne audyty penetracyjne i compliance',
         'kwota_2025': 3500, 'kwota_2026': 3800, 'kwota_2027': 4000,
         'priority': 'obowiązkowy', 'bz': '16.2.1.3', 'is_obligatory': True,
         'uzasadnienie': 'Wymóg KRI i rozporządzenia w sprawie minimalnych wymagań'},
        
        {'dept': 'DSI', 'paragraf': 6060, 'nazwa': 'Utrzymanie SRP',
         'opis': 'System Rejestrów Państwowych - utrzymanie i rozwój',
         'kwota_2025': 12000, 'kwota_2026': 12500, 'kwota_2027': 13000,
         'priority': 'obowiązkowy', 'bz': '16.1.1.1', 'is_obligatory': True,
         'uzasadnienie': 'System krytyczny dla funkcjonowania państwa'},
        
        {'dept': 'DSI', 'paragraf': 6060, 'nazwa': 'Infrastruktura Centralnego Serwera Logów',
         'opis': 'Zakup infrastruktury CSL',
         'kwota_2025': 1181, 'kwota_2026': 500, 'kwota_2027': 500,
         'priority': 'średni', 'bz': '16.1.1.2'},
        
        {'dept': 'DSI', 'paragraf': 4300, 'nazwa': 'System analizy kodu DAST/IAST',
         'opis': 'Rozbudowa systemu do analizy kodu i platform mobilnych',
         'kwota_2025': 1107, 'kwota_2026': 1200, 'kwota_2027': 1300,
         'priority': 'średni', 'bz': '16.1.1.3'},
        
        {'dept': 'DK', 'paragraf': 4300, 'nazwa': 'Portal gov.pl - utrzymanie',
         'opis': 'Utrzymanie i rozwój portalu informacyjnego gov.pl',
         'kwota_2025': 3500, 'kwota_2026': 3700, 'kwota_2027': 3900,
         'priority': 'wysoki', 'bz': '16.4.1.1'},
        
        {'dept': 'DK', 'paragraf': 4210, 'nazwa': 'Kampanie informacyjne',
         'opis': 'Kampanie edukacyjne dotyczące e-usług',
         'kwota_2025': 2000, 'kwota_2026': 2200, 'kwota_2027': 2400,
         'priority': 'uznaniowy', 'bz': '16.4.1.2'},
        
        {'dept': 'BA', 'paragraf': 4210, 'nazwa': 'Materiały biurowe i eksploatacyjne',
         'opis': 'Zakup materiałów biurowych dla MC',
         'kwota_2025': 500, 'kwota_2026': 520, 'kwota_2027': 540,
         'priority': 'niski', 'bz': '16.6.1.1'},
        
        {'dept': 'BA', 'paragraf': 4270, 'nazwa': 'Utrzymanie budynku MC',
         'opis': 'Konserwacja i naprawy budynku ministerstwa',
         'kwota_2025': 2500, 'kwota_2026': 2600, 'kwota_2027': 2700,
         'priority': 'średni', 'bz': '16.6.1.2'},
        
        {'dept': 'BBF', 'paragraf': 4300, 'nazwa': 'System finansowo-księgowy',
         'opis': 'Utrzymanie i licencje systemu ERP',
         'kwota_2025': 1500, 'kwota_2026': 1550, 'kwota_2027': 1600,
         'priority': 'wysoki', 'bz': '16.7.1.1'},
        
        {'dept': 'BBF', 'paragraf': 4170, 'nazwa': 'Szkolenia pracowników BBF',
         'opis': 'Szkolenia z zakresu finansów publicznych',
         'kwota_2025': 200, 'kwota_2026': 210, 'kwota_2027': 220,
         'priority': 'niski', 'bz': '16.7.1.2'},
        
        {'dept': 'DTC', 'paragraf': 4300, 'nazwa': 'Usługi chmurowe - Azure/AWS',
         'opis': 'Opłaty za usługi chmurowe dla systemów MC',
         'kwota_2025': 5000, 'kwota_2026': 6000, 'kwota_2027': 7000,
         'priority': 'wysoki', 'bz': '16.1.2.2'},
        
        {'dept': 'DC', 'paragraf': 4210, 'nazwa': 'Sprzęt sieciowy - MC',
         'opis': 'Zakup urządzeń sieciowych dla Ministerstwa',
         'kwota_2025': 2000, 'kwota_2026': 1500, 'kwota_2027': 1500,
         'priority': 'średni', 'bz': '16.2.1.4'},
        
        {'dept': 'DSI', 'paragraf': 4750, 'nazwa': 'Wymiana komputerów pracowniczych',
         'opis': 'Planowa wymiana stacji roboczych (cykl 4-letni)',
         'kwota_2025': 3000, 'kwota_2026': 3200, 'kwota_2027': 3400,
         'priority': 'średni', 'bz': '16.1.1.4'},
    ]
    
    entries_created = 0
    for entry_data in demo_entries:
        dept = db.query(Department).filter(Department.code == entry_data['dept']).first()
        if not dept:
            continue
        
        priority_map = {
            'obowiązkowy': PriorityLevel.OBOWIAZKOWY,
            'wysoki': PriorityLevel.WYSOKI,
            'średni': PriorityLevel.SREDNI,
            'niski': PriorityLevel.NISKI,
            'uznaniowy': PriorityLevel.UZNANIOWY
        }
        
        entry = BudgetEntry(
            czesc=27,
            paragraf=entry_data.get('paragraf'),
            zrodlo_finansowania='budżet państwa',
            beneficjent_zadaniowy=entry_data.get('bz', ''),
            department_id=dept.id,
            nazwa_zadania=entry_data.get('nazwa'),
            opis_projektu=entry_data.get('opis'),
            szczegolowe_uzasadnienie=entry_data.get('uzasadnienie', entry_data.get('opis')),
            kwota_2025=entry_data.get('kwota_2025', 0),
            kwota_2026=entry_data.get('kwota_2026', 0),
            kwota_2027=entry_data.get('kwota_2027', 0),
            kwota_2028=entry_data.get('kwota_2028', 0),
            kwota_2029=entry_data.get('kwota_2029', 0),
            priority=priority_map.get(entry_data.get('priority', 'średni'), PriorityLevel.SREDNI),
            is_obligatory=entry_data.get('is_obligatory', False),
            status=BudgetStatus.DRAFT,
            nr_umowy=entry_data.get('contract', ''),
            compliance_validated=False
        )
        
        db.add(entry)
        entries_created += 1
    
    db.commit()
    
    total_2025 = db.query(func.sum(BudgetEntry.kwota_2025)).scalar() or 0
    global_limit = db.query(GlobalLimit).filter(GlobalLimit.year == 2025).first()
    if global_limit:
        global_limit.current_total = total_2025
        global_limit.variance = total_2025 - global_limit.total_limit
        db.commit()
    
    return AgentResponse(
        agent_name="Ingestion Agent",
        action="load_demo",
        message=f"Załadowano realistyczne dane demo: {entries_created} pozycji budżetowych",
        data={
            'success': True,
            'entries_created': entries_created,
            'total_2025': total_2025,
            'global_limit': 100000,
            'variance': total_2025 - 100000,
            'departments_with_limits': len(dept_limits)
        },
        warnings=[]
    )

@app.post("/api/ingest/excel-exact")
async def load_exact_excel_data(db: Session = Depends(get_db)):
    """Load EXACT data from Załącznik nr 2 Excel file"""
    import pandas as pd
    
    excel_path = "/home/nealz/Desktop/budzet/docs/Załącznik nr 2 Przykładowa tabela stosowana w procesie planowania budżetu.xlsx"
    
    if not os.path.exists(excel_path):
        raise HTTPException(status_code=404, detail="Excel file not found")
    
    agent = IngestionAgent(db)
    agent.setup_departments()
    agent.setup_global_limit(2025, 100000)
    
    df = pd.read_excel(excel_path, header=0)
    df.columns = [str(c).strip().replace('\n', ' ').lower() for c in df.columns]
    
    df_valid = df[df['2025'].notna() & (df['2025'] > 0)]
    df_valid = df_valid[~df_valid['szczegółowe uzasadnienie'].astype(str).str.contains('Suma|nan', case=False, na=True)]
    
    dept_cache = {}
    for dept in db.query(Department).all():
        dept_cache[dept.code] = dept.id
        dept_cache[dept.code + ' '] = dept.id
    
    entries_created = 0
    warnings = []
    
    for idx, row in df_valid.iterrows():
        try:
            dept_code = str(row.get('departament', 'DTC')).strip()
            dept_id = dept_cache.get(dept_code) or dept_cache.get('DTC')
            
            text = str(row.get('szczegółowe uzasadnienie', '')).lower()
            if any(kw in text for kw in ['eidas', 'ustaw', 'obowiązk', 'rozporządzen']):
                priority = PriorityLevel.OBOWIAZKOWY
                is_obligatory = True
            elif any(kw in text for kw in ['rozwój', 'rozbudowa', 'zakup']):
                priority = PriorityLevel.WYSOKI
                is_obligatory = False
            else:
                priority = PriorityLevel.SREDNI
                is_obligatory = False
            
            entry = BudgetEntry(
                czesc=27,
                paragraf=int(row.get('paragraf')) if pd.notna(row.get('paragraf')) else 6060,
                zrodlo_finansowania=str(row.get('beneficjent', 'budżet państwa'))[:100],
                beneficjent_zadaniowy=str(row.get('bz', ''))[:50] if pd.notna(row.get('bz')) else '',
                department_id=dept_id,
                rodzaj_projektu=str(row.get('rodzaj projektu', ''))[:100] if pd.notna(row.get('rodzaj projektu')) else '',
                opis_projektu=str(row.get('opis projektu', ''))[:500] if pd.notna(row.get('opis projektu')) else '',
                nazwa_zadania=str(row.get('szczegółowe uzasadnienie', ''))[:200] if pd.notna(row.get('szczegółowe uzasadnienie')) else '',
                szczegolowe_uzasadnienie=str(row.get('szczegółowe uzasadnienie', ''))[:1000] if pd.notna(row.get('szczegółowe uzasadnienie')) else '',
                kwota_2025=float(row.get('2025', 0)),
                kwota_2026=float(row.get('2026', 0)) if pd.notna(row.get('2026')) else 0,
                kwota_2027=float(row.get('2027', 0)) if pd.notna(row.get('2027')) else 0,
                kwota_2028=float(row.get('2028', 0)) if pd.notna(row.get('2028')) else 0,
                kwota_2029=float(row.get('2029', 0)) if pd.notna(row.get('2029')) else 0,
                priority=priority,
                is_obligatory=is_obligatory,
                status=BudgetStatus.DRAFT,
                uwagi=str(row.get('uwagi', ''))[:500] if pd.notna(row.get('uwagi')) else '',
                zadanie_inwestycyjne=str(row.get('zadanie inwestycyjne', ''))[:200] if pd.notna(row.get('zadanie inwestycyjne')) else '',
                compliance_validated=False
            )
            
            db.add(entry)
            entries_created += 1
            
        except Exception as e:
            warnings.append(f"Row {idx}: {str(e)}")
    
    db.commit()
    
    total_2025 = db.query(func.sum(BudgetEntry.kwota_2025)).scalar() or 0
    global_limit = db.query(GlobalLimit).filter(GlobalLimit.year == 2025).first()
    if global_limit:
        global_limit.current_total = total_2025
        global_limit.variance = total_2025 - global_limit.total_limit
        db.commit()
    
    return AgentResponse(
        agent_name="Ingestion Agent",
        action="load_excel_exact",
        message=f"Załadowano DOKŁADNE dane z Excela: {entries_created} pozycji",
        data={
            'success': True,
            'entries_created': entries_created,
            'total_2025': total_2025,
            'global_limit': 100000,
            'variance': total_2025 - 100000,
            'source': 'Załącznik nr 2 Przykładowa tabela stosowana w procesie planowania budżetu.xlsx'
        },
        warnings=warnings
    )

@app.get("/api/entries", response_model=List[BudgetEntryResponse])
async def get_entries(
    department_code: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get budget entries with optional filters"""
    
    query = db.query(BudgetEntry)
    
    if department_code:
        query = query.join(Department).filter(Department.code == department_code)
    
    if status:
        query = query.filter(BudgetEntry.status == status)
    
    if priority:
        query = query.filter(BudgetEntry.priority == priority)
    
    entries = query.offset(skip).limit(limit).all()
    
    result = []
    for entry in entries:
        entry_dict = {
            "id": entry.id,
            "czesc": entry.czesc,
            "dzial": entry.dzial,
            "rozdzial": entry.rozdzial,
            "paragraf": entry.paragraf,
            "zrodlo_finansowania": entry.zrodlo_finansowania,
            "beneficjent_zadaniowy": entry.beneficjent_zadaniowy,
            "department_id": entry.department_id,
            "rodzaj_projektu": entry.rodzaj_projektu,
            "opis_projektu": entry.opis_projektu,
            "nazwa_zadania": entry.nazwa_zadania,
            "szczegolowe_uzasadnienie": entry.szczegolowe_uzasadnienie,
            "kwota_2025": entry.kwota_2025 or 0,
            "kwota_2026": entry.kwota_2026 or 0,
            "kwota_2027": entry.kwota_2027 or 0,
            "kwota_2028": entry.kwota_2028 or 0,
            "kwota_2029": entry.kwota_2029 or 0,
            "priority": entry.priority if entry.priority else "średni",
            "is_obligatory": entry.is_obligatory,
            "status": entry.status if entry.status else "draft",
            "etap_dzialan": entry.etap_dzialan,
            "umowy": entry.umowy,
            "nr_umowy": entry.nr_umowy,
            "z_kim_zawarta": entry.z_kim_zawarta,
            "uwagi": entry.uwagi,
            "zadanie_inwestycyjne": entry.zadanie_inwestycyjne,
            "compliance_validated": entry.compliance_validated,
            "compliance_warnings": entry.compliance_warnings,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "total_amount": sum([
                entry.kwota_2025 or 0,
                entry.kwota_2026 or 0,
                entry.kwota_2027 or 0,
                entry.kwota_2028 or 0,
                entry.kwota_2029 or 0
            ])
        }
        result.append(entry_dict)
    
    
    return result

@app.post("/api/entries", response_model=BudgetEntryResponse)
async def create_entry(
    entry: BudgetEntryCreate,
    db: Session = Depends(get_db)
):
    """Create a new budget entry"""
    
    # Verify department exists
    dept = db.query(Department).filter(Department.id == entry.department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
        
    db_entry = BudgetEntry(
        **entry.dict(),
        status='draft',
        compliance_validated=False
    )
    
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    # 📝 AUDIT LOG: Record creation
    create_audit_log(
        db=db,
        entry_id=db_entry.id,
        action="CREATE",
        old_values=None,
        new_values=entry_to_dict(db_entry),
        user_id="system",
        notes=f"Utworzono nową pozycję budżetową: {db_entry.nazwa_zadania or 'bez nazwy'}"
    )
    
    # Run immediate compliance check
    compliance_agent = ComplianceAgent(db)
    compliance_agent.validate_entry(db_entry)
    
    return db_entry

@app.get("/api/entries/{entry_id}")
async def get_entry(entry_id: int, db: Session = Depends(get_db)):
    """Get a single budget entry"""
    
    entry = db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return entry

@app.put("/api/entries/{entry_id}")
async def update_entry(
    entry_id: int, 
    update: BudgetEntryUpdate,
    db: Session = Depends(get_db)
):
    """Update a budget entry"""
    
    entry = db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # 📝 AUDIT LOG: Capture old values before update
    old_values = entry_to_dict(entry)
    
    update_data = update.dict(exclude_unset=True)
    changed_fields = []
    for field, value in update_data.items():
        if hasattr(entry, field):
            old_val = getattr(entry, field)
            if old_val != value:
                changed_fields.append(f"{field}: {old_val} → {value}")
            setattr(entry, field, value)
    
    entry.updated_at = datetime.utcnow()
    entry.compliance_validated = False
    
    db.commit()
    db.refresh(entry)
    
    create_audit_log(
        db=db,
        entry_id=entry_id,
        action="UPDATE",
        old_values=old_values,
        new_values=entry_to_dict(entry),
        user_id="system",
        notes=f"Zmieniono: {'; '.join(changed_fields) if changed_fields else 'brak zmian'}"
    )
    
    compliance_agent = ComplianceAgent(db)
    validation = compliance_agent.validate_entry(entry)
    
    return {
        "entry": entry,
        "compliance": validation
    }

@app.post("/api/entries/{entry_id}/approve")
async def approve_entry(entry_id: int, db: Session = Depends(get_db)):
    """Approve a budget entry"""
    
    entry = db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    old_status = entry.status
    entry.status = 'approved'
    entry.updated_at = datetime.utcnow()
    db.commit()
    
    create_audit_log(
        db=db,
        entry_id=entry_id,
        action="APPROVE",
        old_values={"status": str(old_status)},
        new_values={"status": "approved"},
        user_id="system",
        notes=f"Zatwierdzono pozycję budżetową: {entry.nazwa_zadania or entry_id}"
    )
    
    return {"message": f"Entry {entry_id} approved", "status": "approved"}

@app.post("/api/entries/{entry_id}/reject")
async def reject_entry(entry_id: int, reason: str = "", db: Session = Depends(get_db)):
    """Reject a budget entry"""
    
    entry = db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    old_status = entry.status
    entry.status = BudgetStatus.REJECTED
    entry.uwagi = (entry.uwagi or '') + f"\n[ODRZUCONO: {reason}]"
    entry.updated_at = datetime.utcnow()
    db.commit()
    
    # 📝 AUDIT LOG: Record rejection with reason
    create_audit_log(
        db=db,
        entry_id=entry_id,
        action="REJECT",
        old_values={"status": str(old_status)},
        new_values={"status": "rejected", "reason": reason},
        user_id="system",
        notes=f"Odrzucono: {reason or 'brak powodu'}"
    )
    
    return {"message": f"Entry {entry_id} rejected", "status": "rejected", "reason": reason}

# ============================================================================
# AUDIT HISTORY API ENDPOINTS - Version History & Recovery
# ============================================================================

@app.get("/api/entries/{entry_id}/history")
async def get_entry_history(entry_id: int, db: Session = Depends(get_db)):
    """Get complete version history for a budget entry"""
    
    entry = db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    audit_logs = db.query(BudgetAuditLog).filter(
        BudgetAuditLog.entry_id == entry_id
    ).order_by(BudgetAuditLog.timestamp.desc()).all()
    
    history = []
    for log in audit_logs:
        history.append({
            "id": log.id,
            "action": log.action,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "user_id": log.user_id,
            "notes": log.notes,
            "old_values": json.loads(log.old_values) if log.old_values else None,
            "new_values": json.loads(log.new_values) if log.new_values else None
        })
    
    return {
        "entry_id": entry_id,
        "entry_name": entry.nazwa_zadania or f"Pozycja #{entry_id}",
        "total_changes": len(history),
        "history": history
    }

@app.get("/api/audit/all")
async def get_all_audit_history(
    limit: int = 50,
    action: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get complete audit history across all entries"""
    
    query = db.query(BudgetAuditLog).order_by(BudgetAuditLog.timestamp.desc())
    
    if action:
        query = query.filter(BudgetAuditLog.action == action.upper())
    
    logs = query.limit(limit).all()
    
    history = []
    for log in logs:
        entry = db.query(BudgetEntry).filter(BudgetEntry.id == log.entry_id).first()
        history.append({
            "id": log.id,
            "entry_id": log.entry_id,
            "entry_name": entry.nazwa_zadania if entry else "Usunięta pozycja",
            "action": log.action,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "user_id": log.user_id,
            "notes": log.notes
        })
    
    total = db.query(BudgetAuditLog).count()
    
    return {
        "total_audit_records": total,
        "showing": len(history),
        "history": history
    }

@app.post("/api/entries/{entry_id}/restore/{audit_id}")
async def restore_entry_version(
    entry_id: int,
    audit_id: int,
    db: Session = Depends(get_db)
):
    """Restore entry to a previous version from audit history"""
    
    entry = db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    audit_log = db.query(BudgetAuditLog).filter(
        BudgetAuditLog.id == audit_id,
        BudgetAuditLog.entry_id == entry_id
    ).first()
    
    if not audit_log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    # Get the old values from the audit log
    old_values = json.loads(audit_log.old_values) if audit_log.old_values else None
    
    if not old_values:
        raise HTTPException(status_code=400, detail="No previous values to restore")
    
    # Capture current state before restore
    current_state = entry_to_dict(entry)
    
    # Restore values
    for field, value in old_values.items():
        if hasattr(entry, field) and field != "id":
            setattr(entry, field, value)
    
    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    
    # Log the restore action
    create_audit_log(
        db=db,
        entry_id=entry_id,
        action="RESTORE",
        old_values=current_state,
        new_values=old_values,
        user_id="system",
        notes=f"Przywrócono do wersji z {audit_log.timestamp}"
    )
    
    return {
        "message": f"Entry {entry_id} restored to version from {audit_log.timestamp}",
        "restored_values": old_values,
        "entry": entry_to_dict(entry)
    }

@app.get("/api/entries/{entry_id}/compare/{audit_id_a}/{audit_id_b}")
async def compare_versions(
    entry_id: int,
    audit_id_a: int,
    audit_id_b: int,
    db: Session = Depends(get_db)
):
    """Compare two versions of a budget entry"""
    
    log_a = db.query(BudgetAuditLog).filter(
        BudgetAuditLog.id == audit_id_a,
        BudgetAuditLog.entry_id == entry_id
    ).first()
    
    log_b = db.query(BudgetAuditLog).filter(
        BudgetAuditLog.id == audit_id_b,
        BudgetAuditLog.entry_id == entry_id
    ).first()
    
    if not log_a or not log_b:
        raise HTTPException(status_code=404, detail="One or both audit logs not found")
    
    values_a = json.loads(log_a.new_values) if log_a.new_values else {}
    values_b = json.loads(log_b.new_values) if log_b.new_values else {}
    
    # Find differences
    diffs = []
    all_keys = set(values_a.keys()) | set(values_b.keys())
    for key in all_keys:
        val_a = values_a.get(key)
        val_b = values_b.get(key)
        if val_a != val_b:
            diffs.append({
                "field": key,
                "version_a": val_a,
                "version_b": val_b
            })
    
    return {
        "entry_id": entry_id,
        "version_a": {
            "audit_id": audit_id_a,
            "timestamp": log_a.timestamp.isoformat() if log_a.timestamp else None,
            "action": log_a.action
        },
        "version_b": {
            "audit_id": audit_id_b,
            "timestamp": log_b.timestamp.isoformat() if log_b.timestamp else None,
            "action": log_b.action
        },
        "differences": diffs,
        "total_differences": len(diffs)
    }


@app.get("/api/departments", response_model=List[DepartmentResponse])
async def get_departments(db: Session = Depends(get_db)):
    """Get all departments"""
    return db.query(Department).all()

@app.get("/api/departments/{dept_code}/entries")
async def get_department_entries(
    dept_code: str,
    year: int = 2025,
    db: Session = Depends(get_db)
):
    """Get entries for a specific department (Generative UI view)"""
    
    dept = db.query(Department).filter(Department.code == dept_code).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    entries = db.query(BudgetEntry).filter(
        BudgetEntry.department_id == dept.id
    ).all()
    
    amount_field = f"kwota_{year}"
    total = sum(getattr(e, amount_field) or 0 for e in entries)
    
    return {
        "department": {
            "id": dept.id,
            "code": dept.code,
            "name": dept.name,
            "budget_limit": dept.budget_limit,
            "total_requested": total,
            "variance": total - (dept.budget_limit or 0),
            "is_over_limit": total > (dept.budget_limit or 0)
        },
        "entries": entries,
        "year": year
    }

@app.put("/api/departments/{dept_code}/limit")
async def set_department_limit(
    dept_code: str,
    limit: float,
    db: Session = Depends(get_db)
):
    """Set budget limit for a department"""
    
    dept = db.query(Department).filter(Department.code == dept_code).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    dept.budget_limit = limit
    db.commit()
    
    return {"message": f"Limit for {dept_code} set to {limit}", "department": dept}

@app.post("/api/compliance/validate/{entry_id}")
async def validate_entry_compliance(entry_id: int, db: Session = Depends(get_db)):
    """Validate a single entry against regulations"""
    
    entry = db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    agent = ComplianceAgent(db)
    result = agent.validate_entry(entry)
    
    return AgentResponse(
        agent_name="Compliance Agent",
        action="validate_entry",
        message=f"Validation complete for entry {entry_id}",
        data=result,
        warnings=result.get("warnings", [])
    )

@app.post("/api/compliance/validate-all")
async def validate_all_entries(db: Session = Depends(get_db)):
    """Validate all entries against regulations"""
    
    agent = ComplianceAgent(db)
    results = agent.validate_all_entries()
    summary = agent.get_compliance_summary()
    
    return AgentResponse(
        agent_name="Compliance Agent",
        action="validate_all",
        message=f"Validated {summary['total_entries']} entries. {summary['with_warnings']} have warnings.",
        data={
            "summary": summary,
            "results": results[:20]
        }
    )

@app.get("/api/compliance/summary")
async def get_compliance_summary(db: Session = Depends(get_db)):
    """Get compliance summary"""
    
    agent = ComplianceAgent(db)
    return agent.get_compliance_summary()

@app.get("/api/optimization/gap-analysis")
async def get_gap_analysis(year: int = 2025, db: Session = Depends(get_db)):
    """Analyze budget gap vs limit"""
    
    agent = OptimizationAgent(db)
    result = agent.analyze_budget_gap(year)
    
    return AgentResponse(
        agent_name="Optimization Agent",
        action="gap_analysis",
        message=f"Budget {'exceeds' if result.get('is_over_limit') else 'within'} limit by {abs(result.get('variance', 0)):,.0f} tys. PLN",
        data=result
    )

@app.post("/api/optimization/suggest-cuts")
async def suggest_cuts(
    target_reduction: Optional[float] = None,
    year: int = 2025,
    db: Session = Depends(get_db)
):
    """Generate cut suggestions to meet budget limit"""
    
    agent = OptimizationAgent(db)
    result = agent.generate_cut_suggestions(target_reduction, year)
    
    return AgentResponse(
        agent_name="Limit Negotiator Agent",
        action="suggest_cuts",
        message=result.get("summary", "Analysis complete"),
        data=result,
        warnings=[] if result.get("can_meet_target") else ["Nie można osiągnąć celu bez cięcia zadań obligatoryjnych"]
    )

@app.post("/api/optimization/apply/{entry_id}")
async def apply_optimization(
    entry_id: int,
    action: str,
    new_amount: Optional[float] = None,
    year: int = 2025,
    db: Session = Depends(get_db)
):
    """Apply an optimization suggestion"""
    
    agent = OptimizationAgent(db)
    result = agent.apply_suggestion(entry_id, action, new_amount, year)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return AgentResponse(
        agent_name="Optimization Agent",
        action="apply_optimization",
        message=result.get("message"),
        data=result
    )

@app.get("/api/optimization/department-allocation")
async def get_department_allocation(year: int = 2025, db: Session = Depends(get_db)):
    """Get budget allocation by department"""
    
    agent = OptimizationAgent(db)
    return agent.get_department_allocation(year)

@app.post("/api/conflicts/detect")
async def detect_conflicts(year: int = 2025, db: Session = Depends(get_db)):
    """Detect duplicate/similar budget entries across departments"""
    
    agent = ConflictAgent(db)
    conflicts = agent.detect_conflicts(year)
    summary = agent.get_conflict_summary()
    
    return AgentResponse(
        agent_name="Conflict Resolution Agent",
        action="detect_conflicts",
        message=f"Detected {len(conflicts)} potential duplicates/overlaps",
        data={
            "conflicts": conflicts,
            "summary": summary
        }
    )

@app.post("/api/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: int,
    resolution: str,
    keep_entry_id: Optional[int] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Resolve a detected conflict"""
    
    agent = ConflictAgent(db)
    result = agent.resolve_conflict(conflict_id, resolution, keep_entry_id, notes)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return AgentResponse(
        agent_name="Conflict Resolution Agent",
        action="resolve_conflict",
        message=result.get("message"),
        data=result
    )

@app.get("/api/conflicts/summary")
async def get_conflicts_summary(db: Session = Depends(get_db)):
    """Get conflict detection summary"""
    
    agent = ConflictAgent(db)
    return agent.get_conflict_summary()

@app.get("/api/documents/limit-letter/{dept_code}")
async def generate_limit_letter(
    dept_code: str,
    year: int = 2025,
    new_limit: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Generate formal limit notification letter for a department"""
    
    agent = DocumentAgent(db)
    letter = agent.generate_limit_letter(dept_code, year, new_limit)
    
    if "error" in letter:
        raise HTTPException(status_code=404, detail=letter["error"])
    
    return AgentResponse(
        agent_name="Document Agent (Bureaucrat)",
        action="generate_limit_letter",
        message=f"Generated limit notification letter for {dept_code}",
        data=letter
    )

@app.post("/api/documents/cut-notification/{dept_code}")
async def generate_cut_notification(
    dept_code: str,
    year: int = 2025,
    db: Session = Depends(get_db)
):
    """Generate cut notification letter based on optimization suggestions"""
    
    opt_agent = OptimizationAgent(db)
    suggestions = opt_agent.generate_cut_suggestions(year=year)
    
    dept_cuts = [s for s in suggestions.get("suggestions", []) 
                 if s.get("department") == dept_code]
    
    if not dept_cuts:
        return AgentResponse(
            agent_name="Document Agent (Bureaucrat)",
            action="generate_cut_notification",
            message=f"No cuts required for {dept_code}",
            data={"message": "Brak wymaganych cięć dla tego departamentu"}
        )
    
    doc_agent = DocumentAgent(db)
    letter = doc_agent.generate_cut_notification(dept_code, dept_cuts, year)
    
    return AgentResponse(
        agent_name="Document Agent (Bureaucrat)",
        action="generate_cut_notification",
        message=f"Generated cut notification for {dept_code} ({len(dept_cuts)} items)",
        data=letter
    )

@app.get("/api/documents/justification/{entry_id}")
async def generate_justification(entry_id: int, db: Session = Depends(get_db)):
    """Generate detailed justification narrative for a budget entry"""
    
    agent = DocumentAgent(db)
    justification = agent.generate_justification_narrative(entry_id)
    
    if "error" in justification:
        raise HTTPException(status_code=404, detail=justification["error"])
    
    return AgentResponse(
        agent_name="Document Agent (Bureaucrat)",
        action="generate_justification",
        message=f"Generated justification for entry {entry_id}",
        data=justification
    )

@app.get("/api/documents/summary-report")
async def generate_summary_report(year: int = 2025, db: Session = Depends(get_db)):
    """Generate comprehensive budget summary report for leadership"""
    
    agent = DocumentAgent(db)
    report = agent.generate_summary_report(year)
    
    return AgentResponse(
        agent_name="Document Agent (Bureaucrat)",
        action="generate_summary_report",
        message=f"Generated budget summary report for {year}",
        data=report
    )

@app.get("/api/limits")
async def get_global_limits(db: Session = Depends(get_db)):
    """Get global budget limits"""
    
    limits = db.query(GlobalLimit).all()
    return limits

@app.put("/api/limits/{year}")
async def set_global_limit(year: int, limit: float, db: Session = Depends(get_db)):
    """Set global budget limit for a year"""
    
    existing = db.query(GlobalLimit).filter(GlobalLimit.year == year).first()
    
    if existing:
        existing.total_limit = limit
        existing.variance = (existing.current_total or 0) - limit
    else:
        new_limit = GlobalLimit(year=year, total_limit=limit)
        db.add(new_limit)
    
    db.commit()
    
    return {"message": f"Global limit for {year} set to {limit} tys. PLN"}

@app.get("/api/export/excel")
async def export_to_excel(
    year: int = 2025,
    department_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Export budget data to Excel (.xlsx) file"""
    
    agent = ExportAgent(db)
    excel_file = agent.export_budget_to_excel(year, department_code)
    
    filename = f"budzet_{year}"
    if department_code:
        filename += f"_{department_code}"
    filename += ".xlsx"
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/export/word/limit-letter/{dept_code}")
async def export_limit_letter_to_word(
    dept_code: str,
    year: int = 2025,
    new_limit: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Export limit notification letter to Word (.docx) file"""
    
    try:
        agent = ExportAgent(db)
        docx_file = agent.export_limit_letter_to_docx(dept_code, year, new_limit)
        
        filename = f"pismo_limit_{dept_code}_{year}.docx"
        
        return StreamingResponse(
            docx_file,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/export/word/summary-report")
async def export_summary_report_to_word(year: int = 2025, db: Session = Depends(get_db)):
    """Export budget summary report to Word (.docx) file"""
    
    agent = ExportAgent(db)
    docx_file = agent.export_summary_report_to_docx(year)
    
    filename = f"raport_budzet_{year}.docx"
    
    return StreamingResponse(
        docx_file,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.put("/api/departments/{dept_code}/deadline")
async def set_department_deadline(
    dept_code: str,
    deadline: str,
    db: Session = Depends(get_db)
):
    """Set edit deadline for a department"""
    
    dept = db.query(Department).filter(Department.code == dept_code).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    try:
        dept.edit_deadline = datetime.fromisoformat(deadline)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format: 2025-08-31T23:59:59")
    
    db.commit()
    
    return {
        "message": f"Deadline for {dept_code} set to {deadline}",
        "department": dept_code,
        "deadline": deadline
    }

@app.put("/api/departments/{dept_code}/lock")
async def lock_department_edits(
    dept_code: str,
    locked: bool = True,
    db: Session = Depends(get_db)
):
    """Lock or unlock department edits"""
    
    dept = db.query(Department).filter(Department.code == dept_code).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    dept.edits_locked = locked
    db.commit()
    
    status = "zablokowana" if locked else "odblokowana"
    return {
        "message": f"Edycja dla {dept_code} została {status}",
        "department": dept_code,
        "locked": locked
    }

@app.get("/api/departments/{dept_code}/can-edit")
async def check_department_can_edit(dept_code: str, db: Session = Depends(get_db)):
    """Check if a department can currently edit entries"""
    
    dept = db.query(Department).filter(Department.code == dept_code).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    can_edit = True
    reason = "Edycja dozwolona"
    
    if dept.edits_locked:
        can_edit = False
        reason = "Edycja zablokowana przez administratora"
    elif dept.edit_deadline and datetime.utcnow() > dept.edit_deadline:
        can_edit = False
        reason = f"Termin edycji upłynął: {dept.edit_deadline.strftime('%d.%m.%Y %H:%M')}"
    
    return {
        "department": dept_code,
        "can_edit": can_edit,
        "reason": reason,
        "deadline": dept.edit_deadline.isoformat() if dept.edit_deadline else None,
        "locked": dept.edits_locked
    }

@app.post("/api/entries/{entry_id}/submit")
async def submit_entry_with_validation(entry_id: int, db: Session = Depends(get_db)):
    """Submit entry with hard validation - blocks if validation fails"""
    
    entry = db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    if entry.department:
        dept = entry.department
        if dept.edits_locked:
            raise HTTPException(
                status_code=403, 
                detail="Edycja zablokowana - departament jest zablokowany"
            )
        if dept.edit_deadline and datetime.utcnow() > dept.edit_deadline:
            raise HTTPException(
                status_code=403,
                detail=f"Termin edycji upłynął: {dept.edit_deadline.strftime('%d.%m.%Y %H:%M')}"
            )
    
    compliance_agent = ComplianceAgent(db)
    validation = compliance_agent.validate_entry(entry)
    
    if validation['compliance_score'] < 50:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Nie można przesłać - walidacja nie powiodła się",
                "compliance_score": validation['compliance_score'],
                "errors": validation['warnings'],
                "auto_corrections": validation['auto_corrections']
            }
        )
    
    errors = []
    if not entry.nazwa_zadania and not entry.opis_projektu:
        errors.append("Brak nazwy zadania lub opisu projektu")
    if not entry.paragraf:
        errors.append("Brak paragrafu klasyfikacji budżetowej")
    if not entry.kwota_2025 and not entry.kwota_2026 and not entry.kwota_2027:
        errors.append("Brak kwot finansowych")
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Nie można przesłać - brakujące wymagane pola",
                "errors": errors
            }
        )
    
    entry.status = BudgetStatus.SUBMITTED
    entry.compliance_validated = True
    entry.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": f"Pozycja {entry_id} została przesłana do akceptacji",
        "entry_id": entry_id,
        "status": "submitted",
        "compliance_score": validation['compliance_score']
    }

@app.post("/api/entries/submit-all")
async def submit_all_department_entries(
    department_code: str,
    db: Session = Depends(get_db)
):
    """Submit all entries for a department with validation"""
    
    dept = db.query(Department).filter(Department.code == department_code).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    if dept.edits_locked:
        raise HTTPException(status_code=403, detail="Edycja zablokowana")
    if dept.edit_deadline and datetime.utcnow() > dept.edit_deadline:
        raise HTTPException(status_code=403, detail="Termin edycji upłynął")
    
    entries = db.query(BudgetEntry).filter(
        BudgetEntry.department_id == dept.id,
        BudgetEntry.status == BudgetStatus.DRAFT
    ).all()
    
    submitted = []
    failed = []
    compliance_agent = ComplianceAgent(db)
    
    for entry in entries:
        validation = compliance_agent.validate_entry(entry)
        
        if validation['compliance_score'] >= 50 and (entry.nazwa_zadania or entry.opis_projektu) and entry.paragraf:
            entry.status = BudgetStatus.SUBMITTED
            entry.compliance_validated = True
            submitted.append(entry.id)
        else:
            failed.append({
                "entry_id": entry.id,
                "nazwa": entry.nazwa_zadania or entry.opis_projektu,
                "errors": validation['warnings']
            })
    
    db.commit()
    
    return {
        "department": department_code,
        "submitted_count": len(submitted),
        "failed_count": len(failed),
        "submitted_ids": submitted,
        "failed_entries": failed,
        "message": f"Przesłano {len(submitted)} z {len(entries)} pozycji"
    }

@app.get("/api/orchestrator/analyze")
async def orchestrator_analyze(year: int = 2025, db: Session = Depends(get_db)):
    """Get AI-powered situational analysis of the budget"""
    
    orchestrator = OrchestratorAgent(db)
    return orchestrator.analyze_situation(year)

@app.get("/api/orchestrator/next-actions")
async def orchestrator_next_actions(year: int = 2025, db: Session = Depends(get_db)):
    """Get AI-recommended next actions"""
    
    orchestrator = OrchestratorAgent(db)
    return orchestrator.suggest_next_actions(year)

@app.get("/api/orchestrator/dashboard-intelligence")
async def orchestrator_dashboard(year: int = 2025, db: Session = Depends(get_db)):
    """Get intelligent dashboard with AI insights"""
    
    orchestrator = OrchestratorAgent(db)
    return orchestrator.get_dashboard_intelligence(year)

@app.post("/api/orchestrator/execute/{step}")
async def orchestrator_execute_step(
    step: str,
    year: int = 2025,
    db: Session = Depends(get_db)
):
    """Execute a workflow step with full agent coordination"""
    
    orchestrator = OrchestratorAgent(db)
    return orchestrator.execute_workflow_step(step, {"year": year})

@app.get("/api/forecaster/forecast")
async def forecaster_forecast(
    base_year: int = 2025,
    forecast_years: int = 3,
    db: Session = Depends(get_db)
):
    """Generate multi-year budget forecast"""
    
    forecaster = ForecasterAgent(db)
    return forecaster.forecast_budget(base_year, forecast_years)

@app.get("/api/forecaster/anomalies")
async def forecaster_anomalies(year: int = 2025, db: Session = Depends(get_db)):
    """Detect anomalies in budget data"""
    
    forecaster = ForecasterAgent(db)
    return forecaster.detect_anomalies(year)

@app.post("/api/forecaster/optimize-allocation")
async def forecaster_optimize(db: Session = Depends(get_db)):
    """Optimize budget allocation across multiple years"""
    
    limits = {
        2025: 100000,
        2026: 105000,
        2027: 110000,
        2028: 115000
    }
    
    forecaster = ForecasterAgent(db)
    return forecaster.optimize_multi_year_allocation(limits)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.post("/api/compliance/semantic-validate/{entry_id}")
async def semantic_validate_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    Validate a single entry using LLM-based Semantic Analysis.
    This goes beyond regex to find logic errors and hidden risks.
    """
    
    entry = db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    agent = SemanticComplianceAgent(db)
    result = agent.validate_entry(entry)
    
    return AgentResponse(
        agent_name="Semantic Compliance Agent (AI Judge)",
        action="semantic_validate",
        message="AI Analysis Complete",
        data=result,
        warnings=[result.get("reasoning")] if not result.get("is_compliant") else []
    )
