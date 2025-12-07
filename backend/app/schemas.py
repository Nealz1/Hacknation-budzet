"""
Pydantic schemas for API validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

# Valid values for validation
VALID_PRIORITIES = ['obligatory', 'high', 'medium', 'low', 'discretionary']
VALID_STATUSES = ['draft', 'submitted', 'approved', 'rejected', 'needs_revision']

class DepartmentBase(BaseModel):
    code: str
    name: str
    director_name: Optional[str] = None
    budget_limit: float = 0

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BudgetEntryBase(BaseModel):
    czesc: int = 27
    dzial: Optional[int] = None
    rozdzial: Optional[int] = None
    paragraf: Optional[int] = None
    zrodlo_finansowania: Optional[str] = None
    beneficjent_zadaniowy: Optional[str] = None
    
    rodzaj_projektu: Optional[str] = None
    opis_projektu: Optional[str] = None
    nazwa_zadania: Optional[str] = None
    szczegolowe_uzasadnienie: Optional[str] = None
    
    kwota_2025: float = 0
    kwota_2026: float = 0
    kwota_2027: float = 0
    kwota_2028: float = 0
    kwota_2029: float = 0
    
    priority: str = "medium"
    is_obligatory: bool = False
    
    etap_dzialan: Optional[str] = None
    umowy: Optional[str] = None
    nr_umowy: Optional[str] = None
    z_kim_zawarta: Optional[str] = None
    
    uwagi: Optional[str] = None
    zadanie_inwestycyjne: Optional[str] = None
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v and v not in VALID_PRIORITIES:
            raise ValueError(f'priority must be one of {VALID_PRIORITIES}')
        return v or 'medium'

class BudgetEntryCreate(BudgetEntryBase):
    department_id: int

class BudgetEntryUpdate(BaseModel):
    kwota_2025: Optional[float] = None
    kwota_2026: Optional[float] = None
    kwota_2027: Optional[float] = None
    kwota_2028: Optional[float] = None
    kwota_2029: Optional[float] = None
    priority: Optional[str] = None
    is_obligatory: Optional[bool] = None
    status: Optional[str] = None
    uwagi: Optional[str] = None

class BudgetEntryResponse(BudgetEntryBase):
    id: int
    department_id: Optional[int] = None
    status: str = "draft"
    compliance_validated: bool = False
    compliance_warnings: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    total_amount: Optional[float] = None
    
    class Config:
        from_attributes = True

class ComplianceCheck(BaseModel):
    is_valid: bool
    warnings: List[str] = []
    auto_corrections: List[dict] = []
    suggested_paragraf: Optional[int] = None

class OptimizationSuggestion(BaseModel):
    entry_id: int
    current_amount: float
    suggested_amount: float
    savings: float
    reason: str
    priority: str
    is_deferrable: bool

class BudgetOptimization(BaseModel):
    total_over_limit: float
    target_reduction: float
    suggestions: List[OptimizationSuggestion]
    summary: str

class ConflictEntry(BaseModel):
    entry_a_id: int
    entry_a_name: str
    entry_b_id: int
    entry_b_name: str
    similarity_score: float
    conflict_type: str
    suggested_action: str

class DashboardStats(BaseModel):
    total_entries: int
    total_budget_2025: float
    global_limit_2025: float
    variance: float
    entries_by_status: dict
    entries_by_department: dict
    obligatory_total: float
    discretionary_total: float

class AgentResponse(BaseModel):
    agent_name: str
    action: str
    message: str
    data: Optional[dict] = None
    warnings: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)
