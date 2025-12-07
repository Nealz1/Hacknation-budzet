from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass, asdict
from enum import Enum
import json

from ..models import BudgetEntry, Department, GlobalLimit, BudgetStatus, PriorityLevel

class AgentType(Enum):
    INGESTION = "ingestion"
    COMPLIANCE = "compliance"
    OPTIMIZATION = "optimization"
    CONFLICT = "conflict"
    DOCUMENT = "document"
    EXPORT = "export"
    ORCHESTRATOR = "orchestrator"
    FORECASTER = "forecaster"
    NEGOTIATOR = "negotiator"

@dataclass
class AgentMessage:
    sender: AgentType
    receiver: AgentType
    action: str
    payload: Dict[str, Any]
    priority: int = 5
    timestamp: datetime = None
    correlation_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class WorkflowState:
    current_phase: str
    year: int
    global_limit: float
    total_requests: float
    variance: float
    departments_completed: List[str]
    departments_pending: List[str]
    blocking_issues: List[Dict]
    recommendations: List[Dict]

class OrchestratorAgent:
    
    def __init__(self, db: Session):
        self.db = db
        self.message_queue: List[AgentMessage] = []
        self.workflow_state: Optional[WorkflowState] = None
        self.agent_registry: Dict[AgentType, Any] = {}
        self.knowledge_base: Dict[str, Any] = {}
        
    def initialize_workflow(self, year: int = 2025) -> WorkflowState:
        
        limit = self.db.query(GlobalLimit).filter(GlobalLimit.year == year).first()
        global_limit = limit.total_limit if limit else 0
        
        amount_field = getattr(BudgetEntry, f"kwota_{year}")
        total = self.db.query(func.sum(amount_field)).scalar() or 0
        
        departments = self.db.query(Department).all()
        completed = []
        pending = []
        
        for dept in departments:
            entries = self.db.query(BudgetEntry).filter(
                BudgetEntry.department_id == dept.id
            ).all()
            
            if all(e.status in [BudgetStatus.SUBMITTED, BudgetStatus.APPROVED] for e in entries if entries):
                completed.append(dept.code)
            else:
                pending.append(dept.code)
        
        if len(pending) > len(completed):
            phase = "collection"
        elif total > global_limit:
            phase = "cutting"
        elif len(pending) == 0:
            phase = "finalization"
        else:
            phase = "approval"
        
        self.workflow_state = WorkflowState(
            current_phase=phase,
            year=year,
            global_limit=global_limit,
            total_requests=total,
            variance=total - global_limit,
            departments_completed=completed,
            departments_pending=pending,
            blocking_issues=[],
            recommendations=[]
        )
        
        return self.workflow_state
    
    def analyze_situation(self, year: int = 2025) -> Dict[str, Any]:
        
        state = self.initialize_workflow(year)
        
        analysis = {
            "timestamp": datetime.utcnow().isoformat(),
            "year": year,
            "phase": state.current_phase,
            "summary": "",
            "critical_issues": [],
            "recommended_actions": [],
            "agent_invocations": [],
            "department_status": {},
            "risk_assessment": {}
        }
        
        if state.current_phase == "collection":
            analysis["summary"] = f"Faza zbierania danych. {len(state.departments_pending)} departamentów nie ukończyło."
            analysis["recommended_actions"].append({
                "action": "send_reminders",
                "target": state.departments_pending,
                "priority": "high"
            })
            
        elif state.current_phase == "cutting":
            analysis["summary"] = f"FAZA KRYTYCZNA: Cięcia budżetowe. Przekroczenie: {state.variance:,.0f} tys. PLN"
            
            analysis["agent_invocations"].append({
                "agent": "optimization",
                "action": "generate_cut_suggestions",
                "params": {"year": year}
            })
            
            obligatory = self.db.query(BudgetEntry).filter(
                BudgetEntry.is_obligatory == True
            ).all()
            obligatory_total = sum(getattr(e, f"kwota_{year}") or 0 for e in obligatory)
            
            if obligatory_total > state.global_limit:
                analysis["critical_issues"].append({
                    "type": "OBLIGATORY_EXCEEDS_LIMIT",
                    "severity": "CRITICAL",
                    "message": f"Zadania obligatoryjne ({obligatory_total:,.0f}) przekraczają limit ({state.global_limit:,.0f})!",
                    "recommended_action": "Negocjuj zwiększenie limitu z MF"
                })
        
        elif state.current_phase == "approval":
            analysis["summary"] = "Faza zatwierdzania. Budżet jest w limicie."
            
            analysis["agent_invocations"].append({
                "agent": "compliance",
                "action": "validate_all",
                "params": {}
            })
            
            analysis["agent_invocations"].append({
                "agent": "conflict",
                "action": "detect_conflicts",
                "params": {"year": year}
            })
        
        analysis["risk_assessment"] = self._assess_risks(state, year)
        
        for dept in self.db.query(Department).all():
            entries = self.db.query(BudgetEntry).filter(
                BudgetEntry.department_id == dept.id
            ).all()
            
            if not entries:
                continue
                
            dept_total = sum(getattr(e, f"kwota_{year}") or 0 for e in entries)
            dept_limit = dept.budget_limit or 0
            
            analysis["department_status"][dept.code] = {
                "name": dept.name,
                "total": dept_total,
                "limit": dept_limit,
                "variance": dept_total - dept_limit,
                "status": "over" if dept_total > dept_limit else "within",
                "entries_count": len(entries),
                "draft_count": len([e for e in entries if e.status == BudgetStatus.DRAFT]),
                "submitted_count": len([e for e in entries if e.status == BudgetStatus.SUBMITTED])
            }
        
        return analysis
    
    def _assess_risks(self, state: WorkflowState, year: int) -> Dict[str, Any]:
        
        risks = {
            "overall_level": "low",
            "items": []
        }
        
        if state.variance > 0:
            gap_percent = (state.variance / state.global_limit * 100) if state.global_limit > 0 else 100
            
            if gap_percent > 50:
                risks["overall_level"] = "critical"
                risks["items"].append({
                    "type": "budget_gap",
                    "level": "critical",
                    "description": f"Przekroczenie limitu o {gap_percent:.0f}%",
                    "mitigation": "Wymagane natychmiastowe cięcia lub negocjacje z MF"
                })
            elif gap_percent > 20:
                risks["overall_level"] = "high"
                risks["items"].append({
                    "type": "budget_gap",
                    "level": "high",
                    "description": f"Przekroczenie limitu o {gap_percent:.0f}%",
                    "mitigation": "Przegląd zadań niskiego priorytetu"
                })
        
        current_month = datetime.now().month
        if current_month >= 7 and current_month <= 8:
            if len(state.departments_pending) > 5:
                risks["items"].append({
                    "type": "deadline",
                    "level": "high",
                    "description": f"Faza lipiec-sierpień, {len(state.departments_pending)} departamentów nie ukończyło",
                    "mitigation": "Wysłać przypomnienia z terminem 48h"
                })
        
        unvalidated = self.db.query(BudgetEntry).filter(
            BudgetEntry.compliance_validated == False
        ).count()
        
        if unvalidated > 20:
            risks["items"].append({
                "type": "compliance",
                "level": "medium",
                "description": f"{unvalidated} pozycji bez walidacji zgodności",
                "mitigation": "Uruchom walidację Compliance Agent"
            })
        
        return risks
    
    def suggest_next_actions(self, year: int = 2025) -> List[Dict]:
        
        analysis = self.analyze_situation(year)
        actions = []
        
        if analysis["phase"] == "collection":
            actions.append({
                "priority": 1,
                "action": "📧 Wyślij przypomnienia",
                "description": f"Departamenty oczekujące: {', '.join(self.workflow_state.departments_pending[:5])}",
                "api_call": "/api/documents/reminder-letters",
                "automated": True
            })
            
        elif analysis["phase"] == "cutting":
            actions.append({
                "priority": 1,
                "action": "✂️ Generuj sugestie cięć",
                "description": f"Wymagana redukcja: {self.workflow_state.variance:,.0f} tys. PLN",
                "api_call": "/api/optimization/suggest-cuts",
                "automated": True
            })
            
            actions.append({
                "priority": 2,
                "action": "📊 Przegląd priorytetów",
                "description": "Sprawdź klasyfikację zadań obligatoryjnych vs dyskrecjonalnych",
                "api_call": "/api/entries?priority=discretionary",
                "automated": False
            })
        
        actions.append({
            "priority": 3,
            "action": "✅ Walidacja zgodności",
            "description": "Sprawdź poprawność klasyfikacji budżetowej",
            "api_call": "/api/compliance/validate-all",
            "automated": True
        })
        
        for issue in analysis.get("critical_issues", []):
            if issue["type"] == "OBLIGATORY_EXCEEDS_LIMIT":
                actions.insert(0, {
                    "priority": 0,
                    "action": "🚨 KRYTYCZNE: Negocjuj z MF",
                    "description": issue["message"],
                    "api_call": None,
                    "automated": False,
                    "requires_human": True
                })
        
        return sorted(actions, key=lambda x: x["priority"])
    
    def execute_workflow_step(self, step: str, params: Dict = None) -> Dict:
        
        params = params or {}
        year = params.get("year", 2025)
        
        result = {
            "step": step,
            "status": "completed",
            "agents_invoked": [],
            "outputs": {},
            "next_steps": []
        }
        
        if step == "full_analysis":
            from .compliance_agent import ComplianceAgent
            from .optimization_agent import OptimizationAgent
            from .conflict_agent import ConflictAgent
            
            compliance = ComplianceAgent(self.db)
            compliance.validate_all_entries()
            result["agents_invoked"].append("compliance")
            result["outputs"]["compliance"] = compliance.get_compliance_summary()
            
            optimization = OptimizationAgent(self.db)
            result["agents_invoked"].append("optimization")
            result["outputs"]["optimization"] = optimization.generate_cut_suggestions(year=year)
            
            conflicts = ConflictAgent(self.db)
            result["agents_invoked"].append("conflict")
            result["outputs"]["conflicts"] = {
                "detected": conflicts.detect_conflicts(year),
                "summary": conflicts.get_conflict_summary()
            }
            
            result["outputs"]["situation"] = self.analyze_situation(year)
            result["next_steps"] = self.suggest_next_actions(year)
            
        elif step == "prepare_for_trezor":
            result["outputs"]["trezor_data"] = self._prepare_trezor_export(year)
            
        elif step == "leadership_briefing":
            from .document_agent import DocumentAgent
            
            doc_agent = DocumentAgent(self.db)
            result["agents_invoked"].append("document")
            result["outputs"]["briefing"] = doc_agent.generate_summary_report(year)
            
        return result
    
    def _prepare_trezor_export(self, year: int) -> Dict:
        
        entries = self.db.query(BudgetEntry).filter(
            BudgetEntry.status == BudgetStatus.APPROVED
        ).all()
        
        trezor_data = []
        for entry in entries:
            trezor_data.append({
                "czesc": entry.czesc or 27,
                "dzial": entry.dzial,
                "rozdzial": entry.rozdzial,
                "paragraf": entry.paragraf,
                "projekt": entry.nazwa_zadania or entry.opis_projektu,
                "kwota": getattr(entry, f"kwota_{year}") or 0,
                "uzasadnienie": entry.szczegolowe_uzasadnienie
            })
        
        return {
            "year": year,
            "czesc_budzetowa": 27,
            "nazwa": "Ministerstwo Cyfryzacji",
            "entries_count": len(trezor_data),
            "total": sum(e["kwota"] for e in trezor_data),
            "data": trezor_data
        }
    
    def get_dashboard_intelligence(self, year: int = 2025) -> Dict:
        
        analysis = self.analyze_situation(year)
        actions = self.suggest_next_actions(year)
        
        return {
            "meta": {
                "generated_at": datetime.utcnow().isoformat(),
                "year": year,
                "phase": analysis["phase"]
            },
            "kpis": {
                "total_requests": self.workflow_state.total_requests,
                "global_limit": self.workflow_state.global_limit,
                "variance": self.workflow_state.variance,
                "variance_percent": (self.workflow_state.variance / self.workflow_state.global_limit * 100) if self.workflow_state.global_limit > 0 else 0,
                "departments_complete": len(self.workflow_state.departments_completed),
                "departments_pending": len(self.workflow_state.departments_pending)
            },
            "ai_insights": {
                "summary": analysis["summary"],
                "risk_level": analysis["risk_assessment"]["overall_level"],
                "critical_issues_count": len(analysis["critical_issues"]),
                "top_recommendation": actions[0] if actions else None
            },
            "next_actions": actions[:5],
            "department_breakdown": analysis["department_status"],
            "risk_assessment": analysis["risk_assessment"]
        }
