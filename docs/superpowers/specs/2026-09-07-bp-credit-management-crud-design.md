# BP Credit Management (CRUD) Operation — Design Specification

## Overview
A comprehensive Credit Management & Ledger system enabling Super Admins to perform full CRUD (Create, Read, Update, Delete) operations on Business Partner (BP) credit allocations, top-ups, bonuses, and deductions. 

These credit transactions dynamically integrate into the live credit computation engine, establishing a partner's cumulative credit pool and updating remaining balance calculations across all dashboards in real-time.

---

## 1. Access & Permissions
- **Super Admin Only**: All routes and endpoints strictly restricted using the `@super_admin_required` decorator.
- **Navigation Visibility**: Menus and action buttons for credit management are visible only when `request.user.is_super_admin() == True`.

---

## 2. Data Model Architecture (`dashboard/models.py`)

### `CreditTransaction`
```python
class CreditTransaction(models.Model):
    class TransactionType(models.TextChoices):
        ALLOCATION = 'ALLOCATION', 'Initial / Cycle Allocation'
        TOP_UP = 'TOP_UP', 'Credit Top-Up'
        BONUS = 'BONUS', 'Bonus Credits'
        DEDUCTION = 'DEDUCTION', 'Deduction / Correction'

    business_partner = models.ForeignKey(
        'accounts.BusinessPartner',
        on_delete=models.CASCADE,
        related_name='credit_transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.TOP_UP
    )
    amount = models.PositiveIntegerField(help_text="Amount in credits/characters")
    description = models.CharField(max_length=255, blank=True, help_text="Reason or note for this transaction")
    reference_id = models.CharField(max_length=100, blank=True, help_text="Invoice, PO, or external reference number")
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_credit_transactions'
    )
    transaction_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']
```

### BusinessPartner Methods (`accounts/models.py` or helper in `dashboard/services.py`)
- `get_ledger_credits()`:
  Calculates net credits from active ledger transactions:
  `Sum(ALLOCATION + TOP_UP + BONUS) - Sum(DEDUCTION)`
- Quota Integration:
  If a BP has ledger allocations, `effective_character_limit` = base limit + ledger net credits (or ledger total if manually managing credit pool).
  `remaining_credits` = `max(0, effective_character_limit - character_count)`.

---

## 3. URLs & Views (`admin_panel`)

### URL Routes (`admin_panel/urls.py`):
1. `/admin-panel/credits/` -> `admin_panel:credit_list` (Master Credit Management Table)
2. `/admin-panel/bp/<int:bp_id>/credits/` -> `admin_panel:bp_credit_ledger` (Specific BP Ledger)
3. `/admin-panel/credits/add/` -> `admin_panel:credit_create` (Create credit transaction, optional `?bp=<id>`)
4. `/admin-panel/credits/<int:pk>/edit/` -> `admin_panel:credit_update` (Edit transaction)
5. `/admin-panel/credits/<int:pk>/delete/` -> `admin_panel:credit_delete` (Delete/Void transaction)

### Forms (`admin_panel/forms.py`):
- `CreditTransactionForm`:
  - `business_partner`: ModelChoiceField (Searchable / Select)
  - `transaction_type`: ChoiceField
  - `amount`: IntegerField (min_value=1)
  - `description`: CharField (required/optional)
  - `reference_id`: CharField (optional)
  - `transaction_date`: DateField (date picker widget)

---

## 4. UI / UX Design

### A. Sidebar Navigation (`templates/base.html`)
- In the Super Admin section of the sidebar, add **"Manage Credits"** with icon `lucide:wallet` or `lucide:credit-card`.
- Highlights active when navigating any `/admin-panel/credits/*` routes.

### B. Master Credit Management Page (`admin_panel/templates/admin_panel/credit_list.html`)
- KPI Summary Cards at top:
  - **Total Net Credits Allocated** across all partners
  - **Total Top-ups & Bonuses**
  - **Total Deductions**
  - **Active Partner Accounts**
- Filter & Search Bar:
  - Filter by Business Partner dropdown
  - Filter by Transaction Type (`All`, `Allocation`, `Top-Up`, `Bonus`, `Deduction`)
  - Date Range filter
- Action button: `+ Add Credit Transaction` (prominent button opening form modal or standalone page).
- Data Table:
  - Columns: `#ID`, `Date`, `Business Partner`, `Type` (colored badge), `Amount` (green for +, red for -), `Description / Note`, `Reference ID`, `Created By`, `Actions` (Edit, Delete).

### C. Partner Detail Quick-Access (`admin_panel/templates/admin_panel/bp_detail.html`)
- Added **"Manage Credits"** button in the header action group.
- Dedicated tab/card linking directly to this BP's ledger.

### D. Transaction Form Page (`admin_panel/templates/admin_panel/credit_form.html`)
- Beautiful card layout with Dark/Light mode support.
- Pre-selects BP if accessed from BP detail dossier.
- Validates positive credit amount.

---

## 5. Verification Plan
- Unit tests & automated verification script for CRUD lifecycle:
  - Create transaction -> Verify DB record and balance update.
  - Read ledger -> Verify list endpoint with filters.
  - Update transaction -> Verify updated values and re-calculated balances.
  - Delete transaction -> Verify record removed and balance restored.
  - Permission checks: Non-superadmin cannot access any endpoints (HTTP 302/403).
