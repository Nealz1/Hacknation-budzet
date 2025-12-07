"""
Database models for Budget entries and Classifications
"""
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class BudgetStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"

class PriorityLevel(str, enum.Enum):
    OBOWIAZKOWY = "obowiązkowy"      # Obligatory - required by law
    WYSOKI = "wysoki"                # High priority
    SREDNI = "średni"                # Medium priority  
    NISKI = "niski"                  # Low priority
    UZNANIOWY = "uznaniowy"          # Discretionary

class Department(Base):
    """Departments (Komórki Organizacyjne) in the Ministry"""
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    director_name = Column(String(255))
    budget_limit = Column(Float, default=0)
    
    edit_deadline = Column(DateTime)
    edits_locked = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    budget_entries = relationship("BudgetEntry", back_populates="department")

class BudgetClassification(Base):
    """Budget classification codes from regulations"""
    __tablename__ = "budget_classifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    czesc = Column(Integer)
    dzial = Column(Integer)
    rozdzial = Column(Integer)
    paragraf = Column(Integer, nullable=False)
    nazwa = Column(Text)
    grupa_wydatkow = Column(String(100))
    opis = Column(Text)
    is_investment = Column(Boolean, default=False)
    
class BudgetEntry(Base):
    """Main budget entries table - core of the system"""
    __tablename__ = "budget_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    czesc = Column(Integer, default=27)
    dzial = Column(Integer)
    rozdzial = Column(Integer)
    paragraf = Column(Integer)
    zrodlo_finansowania = Column(String(10))
    beneficjent_zadaniowy = Column(String(50))
    
    department_id = Column(Integer, ForeignKey("departments.id"))
    department = relationship("Department", back_populates="budget_entries")
    
    rodzaj_projektu = Column(String(100))
    opis_projektu = Column(Text)
    nazwa_zadania = Column(Text)
    szczegolowe_uzasadnienie = Column(Text)
    
    kwota_2025 = Column(Float, default=0)
    kwota_2026 = Column(Float, default=0)
    kwota_2027 = Column(Float, default=0)
    kwota_2028 = Column(Float, default=0)
    kwota_2029 = Column(Float, default=0)
    
    priority = Column(String(50), default="średni")
    status = Column(String(50), default="draft")
    is_obligatory = Column(Boolean, default=False)
    
    etap_dzialan = Column(String(50))
    umowy = Column(String(50))
    nr_umowy = Column(String(100))
    z_kim_zawarta = Column(String(255))
    
    uwagi = Column(Text)
    zadanie_inwestycyjne = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    
    compliance_validated = Column(Boolean, default=False)
    compliance_warnings = Column(Text)
    original_paragraf = Column(Integer)

class BudgetConflict(Base):
    """Tracks semantic conflicts between budget entries"""
    __tablename__ = "budget_conflicts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_a_id = Column(Integer, ForeignKey("budget_entries.id"))
    entry_b_id = Column(Integer, ForeignKey("budget_entries.id"))
    conflict_type = Column(String(50))
    similarity_score = Column(Float)
    resolution_status = Column(String(50), default="pending")
    resolution_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class BudgetAuditLog(Base):
    """Audit trail for all changes"""
    __tablename__ = "budget_audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(Integer, ForeignKey("budget_entries.id"))
    action = Column(String(50))
    old_values = Column(Text)
    new_values = Column(Text)
    user_id = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)

class GlobalLimit(Base):
    """Tracks global budget limits from Ministry of Finance"""
    __tablename__ = "global_limits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    total_limit = Column(Float, nullable=False)
    current_total = Column(Float, default=0)
    variance = Column(Float, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)
