from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from datetime import datetime, date
from ..models import BudgetEntry, Department, GlobalLimit, PriorityLevel

class DocumentAgent:
    
    LETTER_TEMPLATES = {
        "limit_notification": {
            "title": "Zawiadomienie o limicie wydatków",
            "formal_opening": "Szanowny Panie Dyrektorze,",
            "formal_closing": "Z poważaniem,"
        },
        "budget_summary": {
            "title": "Informacja zbiorcza o budżecie",
            "formal_opening": "W odpowiedzi na zapytanie,",
            "formal_closing": "Z wyrazami szacunku,"
        },
        "cut_notification": {
            "title": "Informacja o korekcie limitu wydatków",
            "formal_opening": "Szanowny Panie Dyrektorze,",
            "formal_closing": "Z poważaniem,"
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_limit_letter(self, dept_code: str, year: int = 2025, 
                              new_limit: float = None) -> Dict:
        dept = self.db.query(Department).filter(Department.code == dept_code).first()
        if not dept:
            return {"error": f"Department {dept_code} not found"}
        
        global_limit = self.db.query(GlobalLimit).filter(GlobalLimit.year == year).first()
        
        amount_field = getattr(BudgetEntry, f"kwota_{year}")
        entries = self.db.query(BudgetEntry).filter(
            BudgetEntry.department_id == dept.id,
            amount_field > 0
        ).all()
        
        dept_total = sum(getattr(e, f"kwota_{year}") or 0 for e in entries)
        assigned_limit = new_limit or dept.budget_limit or 0
        variance = dept_total - assigned_limit
        
        today = date.today()
        
        letter = {
            "metadata": {
                "document_type": "limit_notification",
                "generated_at": datetime.now().isoformat(),
                "department_code": dept_code,
                "department_name": dept.name,
                "year": year
            },
            "header": {
                "sender": "Biuro Budżetowo-Finansowe\nMinisterstwo Cyfryzacji",
                "date": today.strftime("%d.%m.%Y"),
                "reference": f"BBF-{today.year}/{dept_code}/{today.month:02d}",
                "recipient": f"Pan/Pani Dyrektor\n{dept.name}"
            },
            "content": {
                "title": f"Zawiadomienie o limicie wydatków na rok {year}",
                "opening": self.LETTER_TEMPLATES["limit_notification"]["formal_opening"],
                "body": self._generate_limit_letter_body(
                    dept=dept,
                    year=year,
                    assigned_limit=assigned_limit,
                    current_requests=dept_total,
                    variance=variance,
                    entries=entries
                ),
                "closing": self.LETTER_TEMPLATES["limit_notification"]["formal_closing"],
                "signature": "Dyrektor BBF"
            },
            "attachments": {
                "budget_table": self._generate_budget_table(entries, year),
                "priority_breakdown": self._generate_priority_breakdown(entries, year)
            },
            "data": {
                "assigned_limit": assigned_limit,
                "current_requests": dept_total,
                "variance": variance,
                "is_over_limit": variance > 0,
                "entry_count": len(entries)
            }
        }
        
        return letter
    
    def _generate_limit_letter_body(self, dept: Department, year: int,
                                   assigned_limit: float, current_requests: float,
                                   variance: float, entries: List[BudgetEntry]) -> str:
        
        paragraphs = []
        
        paragraphs.append(
            f"Uprzejmie informuję, że zgodnie z pismem Ministerstwa Finansów, "
            f"limit wydatków dla {dept.name} na rok {year} został ustalony "
            f"na poziomie **{assigned_limit:,.0f} tys. PLN**."
        )
        
        if variance > 0 and assigned_limit > 0:
            over_percent = variance/assigned_limit*100
            paragraphs.append(
                f"Zgłoszone przez Państwa zapotrzebowanie w wysokości "
                f"**{current_requests:,.0f} tys. PLN** przekracza przyznany limit "
                f"o **{variance:,.0f} tys. PLN** ({over_percent:.1f}%)."
            )
            paragraphs.append(
                f"Proszę o dokonanie przeglądu zgłoszonych potrzeb i wskazanie "
                f"zadań do odroczenia lub redukcji w terminie do 7 dni roboczych."
            )
        elif variance > 0:
            paragraphs.append(
                f"Zgłoszone przez Państwa zapotrzebowanie w wysokości "
                f"**{current_requests:,.0f} tys. PLN** przekracza przyznany limit "
                f"o **{variance:,.0f} tys. PLN**."
            )
            paragraphs.append(
                f"Proszę o dokonanie przeglądu zgłoszonych potrzeb i wskazanie "
                f"zadań do odroczenia lub redukcji w terminie do 7 dni roboczych."
            )
        else:
            paragraphs.append(
                f"Zgłoszone przez Państwa zapotrzebowanie w wysokości "
                f"**{current_requests:,.0f} tys. PLN** mieści się w przyznanym limicie. "
                f"Pozostała rezerwa wynosi **{abs(variance):,.0f} tys. PLN**."
            )
        
        obligatory = [e for e in entries if e.is_obligatory]
        if obligatory:
            obligatory_sum = sum(getattr(e, f"kwota_{year}") or 0 for e in obligatory)
            paragraphs.append(
                f"Przypominam, że zadania obligatoryjne (wynikające z przepisów prawa) "
                f"w wysokości **{obligatory_sum:,.0f} tys. PLN** ({len(obligatory)} pozycji) "
                f"muszą zostać zabezpieczone w pierwszej kolejności."
            )
        
        paragraphs.append(
            f"Zgodnie z harmonogramem prac nad budżetem, ostateczne uzgodnienia "
            f"powinny zostać dokonane do końca sierpnia {year-1} r."
        )
        
        return "\n\n".join(paragraphs)
    
    def _generate_budget_table(self, entries: List[BudgetEntry], year: int) -> List[Dict]:
        
        table = []
        for entry in entries:
            amount = getattr(entry, f"kwota_{year}") or 0
            table.append({
                "lp": len(table) + 1,
                "nazwa_zadania": (entry.nazwa_zadania or entry.opis_projektu or "Brak nazwy")[:80],
                "paragraf": entry.paragraf,
                "kwota": amount,
                "priorytet": entry.priority if entry.priority else "medium",
                "status": entry.status if entry.status else "draft",
                "obligatoryjne": "TAK" if entry.is_obligatory else "NIE"
            })
        
        return sorted(table, key=lambda x: x["kwota"], reverse=True)
    
    def _generate_priority_breakdown(self, entries: List[BudgetEntry], year: int) -> Dict:
        
        breakdown = {}
        for priority in PriorityLevel:
            priority_entries = [e for e in entries if e.priority == priority]
            total = sum(getattr(e, f"kwota_{year}") or 0 for e in priority_entries)
            breakdown[priority.value] = {
                "count": len(priority_entries),
                "total": total
            }
        
        return breakdown
    
    def generate_cut_notification(self, dept_code: str, cuts: List[Dict], 
                                 year: int = 2025) -> Dict:
        dept = self.db.query(Department).filter(Department.code == dept_code).first()
        if not dept:
            return {"error": f"Department {dept_code} not found"}
        
        today = date.today()
        total_cuts = sum(c.get("savings", 0) for c in cuts)
        
        letter = {
            "metadata": {
                "document_type": "cut_notification",
                "generated_at": datetime.now().isoformat(),
                "department_code": dept_code,
                "year": year
            },
            "header": {
                "sender": "Biuro Budżetowo-Finansowe\nMinisterstwo Cyfryzacji",
                "date": today.strftime("%d.%m.%Y"),
                "reference": f"BBF-REDUKCJA-{today.year}/{dept_code}/{today.month:02d}",
                "recipient": f"Pan/Pani Dyrektor\n{dept.name}"
            },
            "content": {
                "title": f"Informacja o korekcie budżetu na rok {year}",
                "opening": self.LETTER_TEMPLATES["cut_notification"]["formal_opening"],
                "body": self._generate_cut_letter_body(dept, cuts, total_cuts, year),
                "closing": self.LETTER_TEMPLATES["cut_notification"]["formal_closing"],
                "signature": "Dyrektor BBF"
            },
            "cuts_table": [
                {
                    "lp": i + 1,
                    "nazwa": c.get("nazwa", "")[:60],
                    "akcja": "Odroczenie" if c.get("action") == "defer" else "Redukcja",
                    "kwota_przed": c.get("current_amount", 0),
                    "kwota_po": c.get("suggested_amount", 0),
                    "oszczednosc": c.get("savings", 0),
                    "uzasadnienie": c.get("reason", "")
                }
                for i, c in enumerate(cuts)
            ],
            "summary": {
                "total_cuts": total_cuts,
                "items_affected": len(cuts)
            }
        }
        
        return letter
    
    def _generate_cut_letter_body(self, dept: Department, cuts: List[Dict],
                                  total_cuts: float, year: int) -> str:
        
        paragraphs = []
        
        paragraphs.append(
            f"W nawiązaniu do uzgodnień dotyczących limitu wydatków na rok {year}, "
            f"informuję o konieczności dokonania korekt w budżecie {dept.name}."
        )
        
        deferred = [c for c in cuts if c.get("action") == "defer"]
        reduced = [c for c in cuts if c.get("action") == "reduce"]
        
        if deferred:
            defer_total = sum(c.get("savings", 0) for c in deferred)
            paragraphs.append(
                f"**Zadania do odroczenia na rok {year + 1}:** {len(deferred)} pozycji "
                f"na łączną kwotę **{defer_total:,.0f} tys. PLN**. "
                f"Środki zostaną uwzględnione w planowaniu na kolejny rok budżetowy."
            )
        
        if reduced:
            reduce_total = sum(c.get("savings", 0) for c in reduced)
            paragraphs.append(
                f"**Zadania do redukcji:** {len(reduced)} pozycji "
                f"z oszczędnością **{reduce_total:,.0f} tys. PLN**. "
                f"Redukcje zostały zaplanowane z zachowaniem podstawowej funkcjonalności."
            )
        
        paragraphs.append(
            f"Łączna wartość korekt wynosi **{total_cuts:,.0f} tys. PLN**."
        )
        
        paragraphs.append(
            f"W przypadku pytań lub zastrzeżeń, proszę o kontakt z BBF w terminie 5 dni roboczych."
        )
        
        return "\n\n".join(paragraphs)
    
    def generate_justification_narrative(self, entry_id: int) -> Dict:
        entry = self.db.query(BudgetEntry).filter(BudgetEntry.id == entry_id).first()
        if not entry:
            return {"error": "Entry not found"}
        
        dept = entry.department
        
        is_investment = entry.paragraf and entry.paragraf >= 6000
        is_cybersecurity = any(kw in (entry.nazwa_zadania or "").lower() 
                               for kw in ["cyber", "bezpieczeństwo", "nis", "security"])
        
        narrative = {
            "entry_id": entry_id,
            "title": entry.nazwa_zadania or entry.opis_projektu or "Zadanie budżetowe",
            "department": dept.code if dept else "N/A",
            "classification": {
                "czesc": entry.czesc,
                "paragraf": entry.paragraf,
                "type": "Inwestycyjne" if is_investment else "Bieżące",
                "priority": entry.priority if entry.priority else "medium"
            },
            "financial_summary": {
                "2025": entry.kwota_2025 or 0,
                "2026": entry.kwota_2026 or 0,
                "2027": entry.kwota_2027 or 0,
                "total_3_years": sum([
                    entry.kwota_2025 or 0,
                    entry.kwota_2026 or 0,
                    entry.kwota_2027 or 0
                ])
            },
            "narrative": self._build_justification_text(entry, is_investment, is_cybersecurity),
            "legal_basis": self._identify_legal_basis(entry),
            "risk_if_not_funded": self._assess_risk(entry, is_cybersecurity)
        }
        
        return narrative
    
    def _build_justification_text(self, entry: BudgetEntry, 
                                  is_investment: bool, is_cybersecurity: bool) -> str:
        
        parts = []
        
        parts.append(
            f"Zadanie \"{entry.nazwa_zadania or entry.opis_projektu}\" "
            f"stanowi {'inwestycję' if is_investment else 'wydatek bieżący'} "
            f"w ramach części 27 budżetu państwa (Informatyzacja)."
        )
        
        if entry.szczegolowe_uzasadnienie:
            parts.append(f"**Zakres zadania:** {entry.szczegolowe_uzasadnienie[:500]}")
        
        if entry.is_obligatory:
            parts.append(
                "**Charakter obligatoryjny:** Zadanie wynika z obowiązujących przepisów prawa "
                "i jego realizacja jest niezbędna dla zapewnienia zgodności z wymogami regulacyjnymi."
            )
        elif is_cybersecurity:
            parts.append(
                "**Priorytet strategiczny:** Zadanie związane z cyberbezpieczeństwem "
                "wpisuje się w priorytety Krajowego Systemu Cyberbezpieczeństwa (KSC) "
                "oraz wymogi dyrektywy NIS2."
            )
        
        if entry.umowy:
            parts.append(f"**Status umowy:** {entry.umowy}")
            if entry.z_kim_zawarta:
                parts.append(f"Umowa zawarta z: {entry.z_kim_zawarta}")
        
        return "\n\n".join(parts)
    
    def _identify_legal_basis(self, entry: BudgetEntry) -> List[str]:
        
        bases = []
        content = (entry.nazwa_zadania or "") + " " + (entry.opis_projektu or "")
        content = content.lower()
        
        if "eidas" in content:
            bases.append("Rozporządzenie eIDAS (910/2014)")
        if "nis" in content or "cyber" in content:
            bases.append("Ustawa o Krajowym Systemie Cyberbezpieczeństwa")
            bases.append("Dyrektywa NIS2 (2022/2555)")
        if "dora" in content:
            bases.append("Rozporządzenie DORA (2022/2554)")
        if "epuap" in content or "profil zaufany" in content:
            bases.append("Ustawa o informatyzacji działalności podmiotów realizujących zadania publiczne")
        
        if not bases:
            bases.append("Art. 44 ustawy o finansach publicznych")
        
        return bases
    
    def _assess_risk(self, entry: BudgetEntry, is_cybersecurity: bool) -> str:
        
        if entry.is_obligatory:
            return "WYSOKI - Brak realizacji może skutkować naruszeniem przepisów prawa i sankcjami."
        elif is_cybersecurity:
            return "WYSOKI - Brak realizacji zwiększa podatność na cyberataki i może naruszyć wymogi KSC/NIS2."
        elif entry.priority == PriorityLevel.HIGH:
            return "ŚREDNI - Opóźnienie może wpłynąć na realizację celów strategicznych resortu."
        else:
            return "NISKI - Możliwe odroczenie bez istotnego wpływu na działalność."
    
    def generate_summary_report(self, year: int = 2025) -> Dict:
        global_limit = self.db.query(GlobalLimit).filter(GlobalLimit.year == year).first()
        
        amount_field = getattr(BudgetEntry, f"kwota_{year}")
        dept_data = self.db.query(
            Department.code,
            Department.name,
            Department.budget_limit,
            func.sum(amount_field).label('total'),
            func.count(BudgetEntry.id).label('entry_count')
        ).join(BudgetEntry).group_by(Department.id).all()
        
        priority_totals = {}
        for priority in PriorityLevel:
            total = self.db.query(func.sum(amount_field)).filter(
                BudgetEntry.priority == priority
            ).scalar() or 0
            priority_totals[priority.value] = total
        
        overall_total = sum(d.total or 0 for d in dept_data)
        
        report = {
            "metadata": {
                "document_type": "summary_report",
                "generated_at": datetime.now().isoformat(),
                "year": year
            },
            "executive_summary": {
                "title": f"Informacja zbiorcza o budżecie na rok {year}",
                "global_limit": global_limit.total_limit if global_limit else 0,
                "total_requests": overall_total,
                "variance": overall_total - (global_limit.total_limit if global_limit else 0),
                "is_over_limit": overall_total > (global_limit.total_limit if global_limit else 0),
                "department_count": len(dept_data)
            },
            "department_breakdown": [
                {
                    "code": d.code,
                    "name": d.name,
                    "limit": d.budget_limit or 0,
                    "requested": d.total or 0,
                    "variance": (d.total or 0) - (d.budget_limit or 0),
                    "entry_count": d.entry_count,
                    "status": "🔴" if (d.total or 0) > (d.budget_limit or 0) else "🟢"
                }
                for d in dept_data
            ],
            "priority_breakdown": priority_totals,
            "recommendations": self._generate_recommendations(
                overall_total, 
                global_limit.total_limit if global_limit else 0,
                priority_totals
            )
        }
        
        return report
    
    def _generate_recommendations(self, total: float, limit: float, 
                                  priorities: Dict) -> List[str]:
        
        recs = []
        variance = total - limit
        
        if variance > 0:
            recs.append(
                f"⚠️ Budżet przekracza limit o {variance:,.0f} tys. PLN. "
                f"Wymagana redukcja lub negocjacja zwiększenia limitu z MF."
            )
            
            discretionary = priorities.get("discretionary", 0)
            if discretionary >= variance:
                recs.append(
                    f"✓ Możliwe pokrycie deficytu przez odroczenie wydatków dyskrecjonalnych "
                    f"({discretionary:,.0f} tys. PLN dostępnych do przesunięcia)."
                )
            else:
                recs.append(
                    f"⚠️ Wydatki dyskrecjonalne ({discretionary:,.0f} tys. PLN) nie pokrywają deficytu. "
                    f"Wymagane decyzje dot. zadań o wyższym priorytecie."
                )
        else:
            recs.append(
                f"✓ Budżet mieści się w limicie z rezerwą {abs(variance):,.0f} tys. PLN."
            )
        
        obligatory = priorities.get("obligatory", 0)
        if obligatory > 0:
            recs.append(
                f"🔒 Zadania obligatoryjne: {obligatory:,.0f} tys. PLN - zabezpieczenie wymagane."
            )
        
        return recs
