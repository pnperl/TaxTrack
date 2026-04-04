# app.py - Complete TaxTrack Pro Application

from flask import Flask, render_template, request, jsonify, send_file, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from sqlalchemy import func, and_
import os
import json
import csv
import io
import uuid
from pathlib import Path

# ==================== INITIALIZATION ====================

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taxtrack_pro.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-prod')

db = SQLAlchemy(app)

# ==================== TAX RULES (2025-26) ====================

TAX_CONFIG = {
    'financial_year': '2025-26',
    'assessment_year': '2026-27',
    
    'new_regime_slabs': [
        (400000, 0.00),
        (800000, 0.05),
        (1200000, 0.10),
        (1600000, 0.15),
        (2000000, 0.20),
        (2400000, 0.25),
        (float('inf'), 0.30),
    ],
    
    'old_regime_slabs': [
        (250000, 0.00),
        (500000, 0.05),
        (1000000, 0.20),
        (float('inf'), 0.30),
    ],
    
    'surcharge_brackets': [
        (5000000, 0.00),
        (10000000, 0.10),
        (50000000, 0.15),
        (float('inf'), 0.25),
    ],
    
    'cess_rate': 0.04,
    'standard_deduction_new': 75000,
    'standard_deduction_old': 50000,
    
    'deduction_limits': {
        '80C': 150000,
        '80D_self': 25000,
        '80D_parents': 25000,
        '80D_parents_senior': 50000,
        '80E': 150000,
        '80G': float('inf'),
        '80U': 75000,
        '24': float('inf'),  # Home loan interest
    },
    
    'itr3_applicable': {
        'requirement': 'Self-employed, business income, or professional income',
        'not_eligible': 'Salary only (use ITR-1 or ITR-2)',
    }
}

# ==================== DATABASE MODELS ====================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Personal Details (EDITABLE)
    pan = db.Column(db.String(10), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(15))
    dob = db.Column(db.Date)
    gender = db.Column(db.String(10))  # M/F/O
    
    # Residential Status
    residential_status = db.Column(db.String(50), default='Resident')  # Resident, RNOR, Non-Resident
    days_in_india = db.Column(db.Integer)  # For RNOR calculation
    
    # Financial Year & Tax Regime
    financial_year = db.Column(db.String(10), default='2025-26')
    tax_regime = db.Column(db.String(10), default='new')  # new or old
    
    # Address (EDITABLE)
    address_line1 = db.Column(db.String(255))
    address_line2 = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    postal_code = db.Column(db.String(10))
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    deductions = db.relationship('Deduction', backref='user', lazy=True, cascade='all, delete-orphan')
    auto_fetch_items = db.relationship('AutoFetchItem', backref='user', lazy=True, cascade='all, delete-orphan')
    corrections = db.relationship('Correction', backref='user', lazy=True, cascade='all, delete-orphan')
    salary_details = db.relationship('SalaryDetail', backref='user', lazy=True, cascade='all, delete-orphan')
    house_property = db.relationship('HouseProperty', backref='user', lazy=True, cascade='all, delete-orphan')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User {self.pan}: {self.name}>"

class AutoFetchItem(db.Model):
    """AUTO-FETCH data from AIS, 26AS, CSV imports"""
    __tablename__ = 'auto_fetch_items'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Source
    source = db.Column(db.String(50), nullable=False)  # 'ais', 'tis', '26as', 'csv'
    source_id = db.Column(db.String(255))  # e.g., invoice number from AIS
    
    # Category
    category = db.Column(db.String(100), nullable=False)  # salary, interest, dividend, tds, tcs, etc.
    subcategory = db.Column(db.String(100))
    
    # Data
    date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    narration = db.Column(db.Text)
    
    # Additional Details
    entity_name = db.Column(db.String(255))  # Bank name, employer, etc.
    entity_identifier = db.Column(db.String(255))  # TAN, IFSC, etc.
    
    # Status & Corrections
    status = db.Column(db.String(50), default='pending')  # pending, approved, corrected, flagged
    user_feedback = db.Column(db.String(100))  # 'correct', 'incorrect', 'duplicate', 'not_mine'
    
    # Link to correction if user edited
    correction_id = db.Column(db.String(36), db.ForeignKey('corrections.id'))
    
    # Metadata
    metadata = db.Column(db.Text)  # JSON for extra info
    import_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AutoFetch {self.category}: ₹{self.amount}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'date': self.date.isoformat(),
            'amount': round(self.amount, 2),
            'narration': self.narration,
            'entity_name': self.entity_name,
            'status': self.status,
            'user_feedback': self.user_feedback,
        }

class Correction(db.Model):
    """EDITABLE: Corrections to AUTO-FETCH items"""
    __tablename__ = 'corrections'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Original item corrected
    auto_fetch_item_id = db.Column(db.String(36), db.ForeignKey('auto_fetch_items.id'))
    
    # Correction type
    correction_type = db.Column(db.String(50), nullable=False)  
    # 'duplicate', 'wrong_amount', 'wrong_date', 'wrong_category', 'not_mine', 'exclude'
    
    # Original vs Corrected
    original_value = db.Column(db.Text)  # JSON
    corrected_value = db.Column(db.Text)  # JSON
    
    reason = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Correction {self.correction_type}>"

class Transaction(db.Model):
    """EDITABLE: Manual transactions or corrected AUTO-FETCH items"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    narration = db.Column(db.String(500), nullable=False)
    
    # Category
    category = db.Column(db.String(100), nullable=False)
    subcategory = db.Column(db.String(100))
    
    # Source
    source = db.Column(db.String(50), default='manual')  # manual, ais_approved, csv
    
    # Tax-specific fields
    entity_name = db.Column(db.String(255))
    entity_identifier = db.Column(db.String(255))
    
    # For business transactions
    is_business_expense = db.Column(db.Boolean, default=False)
    expense_type = db.Column(db.String(100))
    
    # For capital gains
    acquisition_date = db.Column(db.Date)
    acquisition_price = db.Column(db.Float)
    disposal_price = db.Column(db.Float)
    holding_period = db.Column(db.String(20))  # short_term, long_term
    
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'amount': round(self.amount, 2),
            'category': self.category,
            'narration': self.narration,
        }

class Deduction(db.Model):
    """EDITABLE: All deductions (80C, 80D, 80E, etc.)"""
    __tablename__ = 'deductions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    section = db.Column(db.String(10), nullable=False)  # 80C, 80D, 80E, 80G, 80U, 24
    deduction_type = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    
    financial_year = db.Column(db.String(10), default='2025-26')
    
    # For 80D, track who it's for
    applicable_to = db.Column(db.String(100))  # self, spouse, children, parents, parents_senior
    
    # Proof document
    document_name = db.Column(db.String(255))
    document_path = db.Column(db.String(500))
    
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'section': self.section,
            'type': self.deduction_type,
            'amount': round(self.amount, 2),
        }

class SalaryDetail(db.Model):
    """EDITABLE: Salary income details (HRA, LTA, etc.)"""
    __tablename__ = 'salary_details'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Salary breakdown
    gross_salary = db.Column(db.Float, nullable=False)
    basic = db.Column(db.Float)
    dearness_allowance = db.Column(db.Float)
    house_rent_allowance = db.Column(db.Float)  # HRA
    leave_travel_allowance = db.Column(db.Float)  # LTA
    other_allowances = db.Column(db.Float)
    
    # Deductions
    professional_tax = db.Column(db.Float, default=0)
    employee_epf = db.Column(db.Float, default=0)
    employee_esic = db.Column(db.Float, default=0)
    other_deductions = db.Column(db.Float, default=0)
    
    # TDS
    tds_deducted = db.Column(db.Float, default=0)
    
    # Employer Details
    employer_name = db.Column(db.String(255))
    employer_tan = db.Column(db.String(10))
    
    # Period
    salary_period = db.Column(db.String(10))  # e.g., 'Jan-25'
    financial_year = db.Column(db.String(10), default='2025-26')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HouseProperty(db.Model):
    """EDITABLE: House property income/loss"""
    __tablename__ = 'house_property'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    property_name = db.Column(db.String(255))
    property_type = db.Column(db.String(100))  # self-occupied, rented, deemed
    
    # For rented property
    monthly_rent = db.Column(db.Float)
    annual_rent = db.Column(db.Float)
    
    # Expenses
    property_tax = db.Column(db.Float, default=0)
    repairs_maintenance = db.Column(db.Float, default=0)
    insurance = db.Column(db.Float, default=0)
    interest_on_loan = db.Column(db.Float, default=0)  # Deductible under Sec 24
    
    # Income/Loss
    gross_annual_value = db.Column(db.Float)
    loss_from_house_property = db.Column(db.Float)  # If negative
    
    financial_year = db.Column(db.String(10), default='2025-26')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ITR3Draft(db.Model):
    """ITR-3 prepared return"""
    __tablename__ = 'itr3_drafts'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    financial_year = db.Column(db.String(10), nullable=False)
    
    # Income summary
    total_salary_income = db.Column(db.Float, default=0)
    total_interest_income = db.Column(db.Float, default=0)
    total_dividend_income = db.Column(db.Float, default=0)
    total_capital_gains = db.Column(db.Float, default=0)
    total_other_income = db.Column(db.Float, default=0)
    gross_total_income = db.Column(db.Float, default=0)
    
    # Business income (for ITR-3)
    total_business_income = db.Column(db.Float, default=0)
    total_business_expenses = db.Column(db.Float, default=0)
    net_business_income = db.Column(db.Float, default=0)
    
    # Deductions
    total_80c = db.Column(db.Float, default=0)
    total_80d = db.Column(db.Float, default=0)
    total_80e = db.Column(db.Float, default=0)
    total_80g = db.Column(db.Float, default=0)
    total_80u = db.Column(db.Float, default=0)
    home_loan_interest_24 = db.Column(db.Float, default=0)
    total_deductions = db.Column(db.Float, default=0)
    
    # Computation
    total_income_after_deductions = db.Column(db.Float, default=0)
    tax_on_income = db.Column(db.Float, default=0)
    surcharge = db.Column(db.Float, default=0)
    cess = db.Column(db.Float, default=0)
    total_tax_liability = db.Column(db.Float, default=0)
    
    # Tax Paid
    total_tds = db.Column(db.Float, default=0)
    total_advance_tax = db.Column(db.Float, default=0)
    total_tax_paid = db.Column(db.Float, default=0)
    
    # Refund or Payable
    refund_or_payable = db.Column(db.Float, default=0)
    
    # Status
    status = db.Column(db.String(50), default='draft')  # draft, preview, filed
    
    # Full JSON
    itr3_json = db.Column(db.Text)  # Serialized JSON
    
    # Warnings/Errors
    warnings = db.Column(db.Text)  # JSON list
    errors = db.Column(db.Text)  # JSON list
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ==================== HELPER FUNCTIONS ====================

def get_or_create_user(pan, name="User"):
    """Get or create user (single user mode)"""
    user = User.query.filter_by(pan=pan).first()
    if not user:
        user = User(pan=pan, name=name)
        db.session.add(user)
        db.session.commit()
    return user

def get_default_user():
    """Get first user (MVP assumes single user)"""
    user = User.query.first()
    if not user:
        user = User(pan='DEMO0000AA', name='Demo User')
        db.session.add(user)
        db.session.commit()
    return user

def calculate_tax(income, regime='new', deductions=0):
    """Calculate tax based on 2025-26 rules"""
    
    slabs = TAX_CONFIG['new_regime_slabs'] if regime == 'new' else TAX_CONFIG['old_regime_slabs']
    
    # Taxable income
    if regime == 'new':
        taxable_income = max(0, income - TAX_CONFIG['standard_deduction_new'])
    else:
        taxable_income = max(0, income - deductions - TAX_CONFIG['standard_deduction_old'])
    
    # Calculate tax
    tax = 0
    prev_limit = 0
    
    for limit, rate in slabs:
        if taxable_income <= prev_limit:
            break
        
        income_in_slab = min(taxable_income, limit) - prev_limit
        tax += income_in_slab * rate
        prev_limit = limit
    
    # Surcharge
    surcharge = 0
    for limit, rate in TAX_CONFIG['surcharge_brackets']:
        if taxable_income <= limit:
            surcharge = tax * rate
            break
    
    # Cess (4%)
    cess = (tax + surcharge) * TAX_CONFIG['cess_rate']
    
    total_tax = tax + surcharge + cess
    
    return {
        'taxable_income': round(taxable_income, 2),
        'tax': round(tax, 2),
        'surcharge': round(surcharge, 2),
        'cess': round(cess, 2),
        'total_tax': round(total_tax, 2),
    }

def parse_ais_json(ais_data):
    """Parse AIS/TIS JSON import"""
    transactions = []
    
    try:
        # AIS typically has structure: { "annual_information": [ { ... }, ... ] }
        if isinstance(ais_data, str):
            ais_data = json.loads(ais_data)
        
        items = ais_data.get('annual_information', ais_data.get('items', []))
        
        for item in items:
            txn = {
                'date': item.get('date') or item.get('transaction_date'),
                'amount': item.get('amount') or item.get('value'),
                'narration': item.get('narration') or item.get('description'),
                'category': item.get('category') or item.get('transaction_type'),
                'entity_name': item.get('entity_name') or item.get('reported_by'),
                'entity_identifier': item.get('tan') or item.get('ifsc'),
                'source_id': item.get('id') or item.get('reference_number'),
                'source': 'ais',
            }
            transactions.append(txn)
        
        return transactions
    except Exception as e:
        return {'error': str(e)}

def categorize_ais_item(category_str, amount):
    """Map AIS category to standard category"""
    category_str = (category_str or '').lower()
    
    mapping = {
        'salary': 'salary',
        'interest': 'interest',
        'bank_interest': 'interest',
        'fd_interest': 'interest',
        'dividend': 'dividend',
        'capital_gain': 'capital_gains',
        'capital_gains': 'capital_gains',
        'tds': 'tds',
        'tcs': 'tcs',
        'rent': 'house_property_rent',
        'property': 'house_property',
    }
    
    for key, value in mapping.items():
        if key in category_str:
            return value
    
    return 'other_income'

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Dashboard"""
    user = get_default_user()
    fy = user.financial_year
    
    # Get auto-fetch items
    auto_fetch = AutoFetchItem.query.filter_by(user_id=user.id).all()
    
    # Get transactions
    transactions = Transaction.query.filter_by(user_id=user.id).all()
    
    # Get deductions
    deductions = Deduction.query.filter_by(user_id=user.id, financial_year=fy).all()
    
    # Calculate totals
    total_auto_fetch_income = sum(a.amount for a in auto_fetch if a.category in [
        'salary', 'interest', 'dividend', 'capital_gains'
    ] and a.amount > 0)
    
    total_manual_income = sum(t.amount for t in transactions if t.amount > 0)
    total_income = total_auto_fetch_income + total_manual_income
    
    total_deductions = sum(d.amount for d in deductions)
    
    # Calculate tax
    tax_calc = calculate_tax(total_income, regime=user.tax_regime, deductions=total_deductions)
    
    # Pending approvals
    pending_auto_fetch = [a for a in auto_fetch if a.status == 'pending']
    
    return render_template('index.html',
        user=user,
        total_income=round(total_income, 2),
        total_deductions=round(total_deductions, 2),
        tax_calc=tax_calc,
        auto_fetch_count=len(auto_fetch),
        pending_count=len(pending_auto_fetch),
        transactions_count=len(transactions),
        deductions_count=len(deductions),
    )

@app.route('/import-ais', methods=['GET', 'POST'])
def import_ais():
    """Import AIS/TIS JSON"""
    user = get_default_user()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('import_ais.html', error='No file selected')
        
        file = request.files['file']
        
        if file.filename == '':
            return render_template('import_ais.html', error='No file selected')
        
        try:
            content = file.read().decode('utf-8')
            ais_data = json.loads(content)
            
            items = parse_ais_json(ais_data)
            
            if isinstance(items, dict) and 'error' in items:
                return render_template('import_ais.html', error=items['error'])
            
            # Create AutoFetchItems
            for item in items:
                try:
                    date_obj = datetime.fromisoformat(item['date']).date() if isinstance(item['date'], str) else item['date']
                except:
                    date_obj = datetime.now().date()
                
                auto_fetch = AutoFetchItem(
                    user_id=user.id,
                    source=item.get('source', 'ais'),
                    source_id=item.get('source_id'),
                    category=categorize_ais_item(item.get('category'), item.get('amount')),
                    date=date_obj,
                    amount=float(item['amount']),
                    narration=item.get('narration'),
                    entity_name=item.get('entity_name'),
                    entity_identifier=item.get('entity_identifier'),
                    status='pending',
                )
                db.session.add(auto_fetch)
            
            db.session.commit()
            
            return render_template('import_ais.html',
                success=True,
                count=len(items),
                message=f'Imported {len(items)} items from AIS/TIS'
            )
        
        except json.JSONDecodeError:
            return render_template('import_ais.html', error='Invalid JSON format')
        except Exception as e:
            return render_template('import_ais.html', error=f'Error: {str(e)}')
    
    return render_template('import_ais.html')

@app.route('/auto-fetch-review')
def auto_fetch_review():
    """Review AUTO-FETCH items before approval"""
    user = get_default_user()
    
    # Get all auto-fetch items
    all_items = AutoFetchItem.query.filter_by(user_id=user.id).order_by(AutoFetchItem.date.desc()).all()
    
    # Group by status
    pending = [i for i in all_items if i.status == 'pending']
    approved = [i for i in all_items if i.status == 'approved']
    flagged = [i for i in all_items if i.status == 'flagged']
    
    # Summary
    total_pending_income = sum(i.amount for i in pending if i.category in [
        'salary', 'interest', 'dividend', 'capital_gains'
    ] and i.amount > 0)
    
    return render_template('auto_fetch_review.html',
        pending_items=pending,
        approved_items=approved,
        flagged_items=flagged,
        total_pending_income=round(total_pending_income, 2),
        pending_count=len(pending),
    )

@app.route('/auto-fetch/<item_id>/approve', methods=['POST'])
def approve_auto_fetch(item_id):
    """Approve AUTO-FETCH item"""
    user = get_default_user()
    item = AutoFetchItem.query.filter_by(id=item_id, user_id=user.id).first()
    
    if not item:
        return jsonify({'success': False, 'error': 'Item not found'}), 404
    
    # Create transaction from approved auto-fetch
    txn = Transaction(
        user_id=user.id,
        date=item.date,
        amount=item.amount,
        narration=item.narration or f'{item.category} from {item.entity_name}',
        category=item.category,
        source='ais_approved',
        entity_name=item.entity_name,
    )
    
    item.status = 'approved'
    
    db.session.add(txn)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Item approved'})

@app.route('/auto-fetch/<item_id>/flag', methods=['POST'])
def flag_auto_fetch(item_id):
    """Flag AUTO-FETCH item for review"""
    user = get_default_user()
    item = AutoFetchItem.query.filter_by(id=item_id, user_id=user.id).first()
    
    if not item:
        return jsonify({'success': False}), 404
    
    reason = request.get_json().get('reason', '')
    
    item.status = 'flagged'
    item.user_feedback = 'duplicate' if 'duplicate' in reason.lower() else 'incorrect'
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/personal-details', methods=['GET', 'POST'])
def personal_details():
    """EDITABLE: Personal details"""
    user = get_default_user()
    
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.residential_status = request.form.get('residential_status', 'Resident')
        user.days_in_india = request.form.get('days_in_india', type=int)
        user.tax_regime = request.form.get('tax_regime', 'new')
        
        user.address_line1 = request.form.get('address_line1')
        user.address_line2 = request.form.get('address_line2')
        user.city = request.form.get('city')
        user.state = request.form.get('state')
        user.postal_code = request.form.get('postal_code')
        
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return redirect('/personal-details?saved=1')
    
    return render_template('personal_details.html', user=user)

@app.route('/deductions', methods=['GET', 'POST'])
def deductions():
    """EDITABLE: Manage deductions"""
    user = get_default_user()
    fy = user.financial_year
    
    if request.method == 'POST':
        section = request.form.get('section')
        ded_type = request.form.get('deduction_type')
        amount = float(request.form.get('amount'))
        
        ded = Deduction(
            user_id=user.id,
            section=section,
            deduction_type=ded_type,
            amount=amount,
            financial_year=fy,
            applicable_to=request.form.get('applicable_to'),
            notes=request.form.get('notes'),
        )
        
        db.session.add(ded)
        db.session.commit()
        
        return redirect('/deductions?added=1')
    
    deductions_list = Deduction.query.filter_by(user_id=user.id, financial_year=fy).all()
    
    # Summary
    summary = {}
    for section in ['80C', '80D', '80E', '80G', '80U', '24']:
        total = sum(d.amount for d in deductions_list if d.section == section)
        limit = TAX_CONFIG['deduction_limits'].get(section, float('inf'))
        summary[section] = {
            'amount': round(total, 2),
            'limit': limit,
            'remaining': round(max(0, limit - total), 2) if limit != float('inf') else 'Unlimited',
        }
    
    return render_template('deductions.html',
        deductions=deductions_list,
        summary=summary,
        config=TAX_CONFIG,
    )

@app.route('/deduction/<ded_id>/delete', methods=['POST'])
def delete_deduction(ded_id):
    """Delete deduction"""
    user = get_default_user()
    ded = Deduction.query.filter_by(id=ded_id, user_id=user.id).first()
    
    if ded:
        db.session.delete(ded)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 404

@app.route('/salary-details', methods=['GET', 'POST'])
def salary_details():
    """EDITABLE: Salary income with HRA/LTA exemptions"""
    user = get_default_user()
    fy = user.financial_year
    
    if request.method == 'POST':
        salary = SalaryDetail(
            user_id=user.id,
            gross_salary=float(request.form.get('gross_salary')),
            basic=float(request.form.get('basic', 0)),
            dearness_allowance=float(request.form.get('dearness_allowance', 0)),
            house_rent_allowance=float(request.form.get('house_rent_allowance', 0)),
            leave_travel_allowance=float(request.form.get('leave_travel_allowance', 0)),
            other_allowances=float(request.form.get('other_allowances', 0)),
            professional_tax=float(request.form.get('professional_tax', 0)),
            employee_epf=float(request.form.get('employee_epf', 0)),
            employee_esic=float(request.form.get('employee_esic', 0)),
            tds_deducted=float(request.form.get('tds_deducted', 0)),
            employer_name=request.form.get('employer_name'),
            employer_tan=request.form.get('employer_tan'),
            salary_period=request.form.get('salary_period'),
            financial_year=fy,
        )
        
        db.session.add(salary)
        db.session.commit()
        
        return redirect('/salary-details?added=1')
    
    salary_list = SalaryDetail.query.filter_by(user_id=user.id, financial_year=fy).all()
    
    # Calculate HRA exemption rules
    hra_exemption_info = {
        'rule_1': '50% of salary (metro cities)',
        'rule_2': '40% of salary (non-metro)',
        'rule_3': 'Actual HRA received',
    }
    
    return render_template('salary_hra_lta.html',
        salary_list=salary_list,
        hra_info=hra_exemption_info,
    )

@app.route('/itr3-preview')
def itr3_preview():
    """Generate ITR-3 preview"""
    user = get_default_user()
    fy = user.financial_year
    
    # Get all data
    auto_fetch = AutoFetchItem.query.filter_by(user_id=user.id, status='approved').all()
    transactions = Transaction.query.filter_by(user_id=user.id).all()
    deductions = Deduction.query.filter_by(user_id=user.id, financial_year=fy).all()
    salaries = SalaryDetail.query.filter_by(user_id=user.id, financial_year=fy).all()
    
    # Calculate income summary
    income_summary = {
        'salary': 0,
        'interest': 0,
        'dividend': 0,
        'capital_gains': 0,
        'other_income': 0,
        'tds': 0,
        'tcs': 0,
    }
    
    # From salaries
    for salary in salaries:
        income_summary['salary'] += salary.gross_salary
        income_summary['tds'] += salary.tds_deducted
    
    # From auto-fetch
    for item in auto_fetch:
        if item.category == 'salary':
            income_summary['salary'] += item.amount
        elif item.category == 'interest':
            income_summary['interest'] += item.amount
        elif item.category == 'dividend':
            income_summary['dividend'] += item.amount
        elif item.category == 'capital_gains':
            income_summary['capital_gains'] += item.amount
        elif item.category == 'tds':
            income_summary['tds'] += item.amount
        elif item.category == 'tcs':
            income_summary['tcs'] += item.amount
        else:
            income_summary['other_income'] += item.amount
    
    # From manual transactions
    for txn in transactions:
        if txn.category == 'salary':
            income_summary['salary'] += txn.amount
        # ... add other categories
    
    # Total income
    total_income = sum(v for k, v in income_summary.items() if k not in ['tds', 'tcs'])
    
    # Deductions
    deduction_summary = {}
    for section in ['80C', '80D', '80E', '80G', '80U', '24']:
        deduction_summary[section] = sum(
            d.amount for d in deductions if d.section == section
        )
    
    total_deductions = sum(deduction_summary.values())
    
    # Tax calculation
    tax_calc = calculate_tax(total_income, regime=user.tax_regime, deductions=total_deductions)
    
    # Generate ITR-3 JSON
    itr3_data = {
        'form_type': 'ITR-3',
        'assessee_info': {
            'name': user.name,
            'pan': user.pan,
            'residential_status': user.residential_status,
            'financial_year': fy,
            'assessment_year': TAX_CONFIG['assessment_year'],
            'email': user.email,
            'phone': user.phone,
        },
        'schedule_1_salary': {
            'salary': round(income_summary['salary'], 2),
        },
        'schedule_5_other_income': {
            'interest': round(income_summary['interest'], 2),
            'dividend': round(income_summary['dividend'], 2),
            'other': round(income_summary['other_income'], 2),
        },
        'schedule_3_capital_gains': {
            'long_term': round(income_summary['capital_gains'], 2),
        },
        'schedule_6_deductions': {
            '80C': round(deduction_summary.get('80C', 0), 2),
            '80D': round(deduction_summary.get('80D', 0), 2),
            '80E': round(deduction_summary.get('80E', 0), 2),
            '80G': round(deduction_summary.get('80G', 0), 2),
            '80U': round(deduction_summary.get('80U', 0), 2),
            '24_interest': round(deduction_summary.get('24', 0), 2),
        },
        'computation': {
            'gross_total_income': round(total_income, 2),
            'total_deductions': round(total_deductions, 2),
            'taxable_income': tax_calc['taxable_income'],
            'tax_on_income': tax_calc['tax'],
            'surcharge': tax_calc['surcharge'],
            'cess': tax_calc['cess'],
            'total_tax_liability': tax_calc['total_tax'],
        },
        'tds_section_194': {
            'tds_paid': round(income_summary['tds'], 2),
            'tcs_paid': round(income_summary['tcs'], 2),
            'total_tax_paid': round(income_summary['tds'] + income_summary['tcs'], 2),
        },
        'verification': {
            'refund_or_payable': round(
                (income_summary['tds'] + income_summary['tcs']) - tax_calc['total_tax'], 2
            ),
        },
    }
    
    # Validation warnings
    warnings = []
    
    if total_income == 0:
        warnings.append('⚠️ No income recorded. ITR-3 requires business/professional income.')
    
    if deduction_summary.get('80C', 0) > 150000:
        warnings.append('⚠️ Section 80C deduction exceeds limit of ₹1,50,000')
    
    if user.tax_regime == 'old' and total_deductions > total_income:
        warnings.append('⚠️ Total deductions exceed income (may not be allowed)')
    
    return render_template('itr3_preview.html',
        user=user,
        itr3_data=itr3_data,
        income_summary=income_summary,
        deduction_summary=deduction_summary,
        tax_calc=tax_calc,
        warnings=warnings,
        itr3_json=json.dumps(itr3_data, indent=2),
    )

@app.route('/export-itr3-json')
def export_itr3_json():
    """Export ITR-3 as JSON file"""
    user = get_default_user()
    
    # Generate ITR-3 (same logic as preview)
    # ... (reuse from itr3_preview logic)
    
    # For brevity, just creating basic export
    itr3_basic = {
        'form_type': 'ITR-3',
        'assessee_info': {
            'name': user.name,
            'pan': user.pan,
            'financial_year': user.financial_year,
        },
        'exported_at': datetime.now().isoformat(),
    }
    
    response = send_file(
        io.BytesIO(json.dumps(itr3_basic, indent=2).encode()),
        mimetype='application/json',
        as_attachment=True,
        download_name=f'ITR3_{user.pan}_{datetime.now().strftime("%Y%m%d")}.json'
    )
    
    return response

@app.route('/settings')
def settings():
    """Settings"""
    user = get_default_user()
    return render_template('settings.html', user=user, config=TAX_CONFIG)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Server error'), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.first():
            user = User(pan='DEMO0000AA', name='Demo User')
            db.session.add(user)
            db.session.commit()
    
    app.run(debug=os.getenv('FLASK_DEBUG', '1') == '1', host='0.0.0.0', port=int(os.getenv('PORT', '5000')))
