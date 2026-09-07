# BP Credit Management (CRUD) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide Super Admins with a dedicated Credit Management (CRUD) system to create, view, edit, and delete credit transactions (allocations, top-ups, bonuses, deductions) for each Business Partner, dynamically updating balances across the CRM.

**Architecture:** A new `CreditTransaction` model in the `dashboard` app tracks all credit activities. Super Admin views in `admin_panel` provide full CRUD operations with filtering, search, and ledger views. A helper service integrates ledger totals into partner quota calculations, feeding into live dashboard boxes and the BP detail page.

**Tech Stack:** Django 5, SQLite, Tailwind CSS, Lucide icons (Iconify), HTML5/JS.

## Global Constraints
- Restricted strictly to Super Admins (`@super_admin_required`).
- Consistent UI with existing Dark/Light mode theme.
- All amounts validated as positive integers with signed representations (+ for allocations/top-ups/bonuses, - for deductions).
- Real-time updates to credit limits and remaining balances across both Admin and BP dashboards.

---

### Task 1: Model & Migrations

**Files:**
- Modify: `dashboard/models.py`
- Modify: `accounts/models.py` (add convenience method)
- Test: `tests/test_credit_models.py`

**Interfaces:**
- Produces: `CreditTransaction` model with fields `business_partner`, `transaction_type`, `amount`, `description`, `reference_id`, `created_by`, `transaction_date`, `created_at`, `updated_at`.
- Produces: `bp.get_ledger_credits()` returning net integer credits.

- [ ] **Step 1: Write model test**
```python
# tests/test_credit_models.py
import pytest
from accounts.models import User, BusinessPartner
from dashboard.models import CreditTransaction

@pytest.mark.django_db
def test_credit_transaction_net_calculation():
    user = User.objects.create_user(username='bp_user', password='password123')
    bp = BusinessPartner.objects.create(user=user, company_name='Acme Corp', email='acme@example.com')
    
    CreditTransaction.objects.create(
        business_partner=bp,
        transaction_type=CreditTransaction.TransactionType.ALLOCATION,
        amount=10000
    )
    CreditTransaction.objects.create(
        business_partner=bp,
        transaction_type=CreditTransaction.TransactionType.TOP_UP,
        amount=5000
    )
    CreditTransaction.objects.create(
        business_partner=bp,
        transaction_type=CreditTransaction.TransactionType.DEDUCTION,
        amount=2000
    )
    assert bp.get_ledger_credits() == 13000
```

- [ ] **Step 2: Add `CreditTransaction` to `dashboard/models.py` and `get_ledger_credits` to `BusinessPartner`**
- [ ] **Step 3: Run `python manage.py makemigrations` and `python manage.py migrate`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit changes**

---

### Task 2: Forms & Views for Credit CRUD

**Files:**
- Modify: `admin_panel/forms.py`
- Modify: `admin_panel/views.py`
- Modify: `admin_panel/urls.py`

**Interfaces:**
- Produces:
  - `CreditTransactionForm`
  - Views: `credit_list`, `bp_credit_ledger`, `credit_create`, `credit_update`, `credit_delete`
  - URLs under `/admin-panel/credits/`

- [ ] **Step 1: Create `CreditTransactionForm` in `admin_panel/forms.py`**
- [ ] **Step 2: Implement CRUD views in `admin_panel/views.py` decorated with `@super_admin_required`**
- [ ] **Step 3: Register routes in `admin_panel/urls.py`**
- [ ] **Step 4: Verify views return 200 and handle POST redirects**
- [ ] **Step 5: Commit changes**

---

### Task 3: Templates for Credit Management & Forms

**Files:**
- Create: `admin_panel/templates/admin_panel/credit_list.html`
- Create: `admin_panel/templates/admin_panel/credit_form.html`

**Interfaces:**
- Produces:
  - `credit_list.html`: Table with summary cards, BP dropdown filter, transaction type filter, search, and action links.
  - `credit_form.html`: Form with inputs for BP, type, amount, description, reference, and date.

- [ ] **Step 1: Build `credit_list.html` with Tailwind CSS, KPI cards, and responsive table**
- [ ] **Step 2: Build `credit_form.html` supporting both Add and Edit modes**
- [ ] **Step 3: Test template rendering in browser / test client**
- [ ] **Step 4: Commit changes**

---

### Task 4: UI Navigation & Quota Integration

**Files:**
- Modify: `templates/base.html` (sidebar link)
- Modify: `admin_panel/templates/admin_panel/bp_detail.html` (button in header)
- Modify: `admin_panel/views.py` (bp_detail view balance computation)
- Modify: `dashboard/views.py` (bp_dashboard view balance computation)

**Interfaces:**
- Sidebar displays "Manage Credits" for Super Admin.
- BP Detail displays "Manage Credits" button.
- Quota engine includes ledger net balance into `character_limit` and `remaining`.

- [ ] **Step 1: Add sidebar link to `templates/base.html`**
- [ ] **Step 2: Add "Manage Credits" button to `admin_panel/bp_detail.html`**
- [ ] **Step 3: Update `admin_panel/views.py` and `dashboard/views.py` balance calculations**
- [ ] **Step 4: Commit changes**

---

### Task 5: End-to-End Verification & Automated Testing

**Files:**
- Create: `tests/test_credit_crud_e2e.py`

- [ ] **Step 1: Write automated end-to-end test verifying full CRUD flow**
- [ ] **Step 2: Verify non-superadmin users are blocked**
- [ ] **Step 3: Run Django test runner**
- [ ] **Step 4: Commit and push changes to git**
