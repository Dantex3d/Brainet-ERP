# Fees Module Documentation

## Overview
The **Fees Module** (fees app) is a comprehensive fee management system for Brainet Analytics. It allows schools to:
- Create fee structures with multiple components (tuition, boarding, activities, etc.)
- Generate professional fee invoices
- Track payment status (Pending, Paid, Cancelled)
- Accept multiple payment methods (M-Pesa, Bank Transfer, Cash, Other)
- Generate professional receipts with school branding, logos, and watermarks
- Support multiple school names for officiality

## Features

### 1. **Fee Structures**
Define flexible fee components by school and term:
- Multiple fee components (Tuition, Boarding, Lab Fees, Activity Fees, etc.)
- Term-based fee planning
- Easy component management
- Total amount calculation

### 2. **Professional Invoices**
Generate invoices with:
- Unique invoice numbers (FEE-XXXXXXXX format)
- Payer name tracking
- Due date management
- Flexible payment methods
- Payment reference tracking

### 3. **Payment Tracking**
- Track payment status: Pending, Paid, Overdue
- Record payment references (M-Pesa codes, bank transaction IDs)
- Automatic timestamp for payments
- Payment method recording

### 4. **Professional Receipts**
Each receipt includes:
- **School Header**: School name, logo, motto, contact details
- **Watermark**: School name watermark in background (semi-transparent)
- **Header Underline**: Decorative line with school colors
- **Multiple School Names**: For official certification
- **Invoice Details**: Number, payer, amount, status
- **Payment Information**: Method, reference, date
- **Professional Design**: Print-ready, PDF-exportable
- **Footer**: Official receipt certification

### 5. **User Roles**
Access is controlled by role:
- **Superuser**: Can create/manage invoices for all schools
- **Principal**: Can create/manage invoices for their school
- **DOS**: Can create/manage invoices for their school
- **Bursar**: Primary role for fee management; can create/manage invoices
- **Students**: View-only access (if enabled)

## Models

### FeeStructure
Represents a set of fee components for a school in a term.

```python
FeeStructure(
    school,           # ForeignKey to School
    title,            # e.g., "2024 Term 1 Fees"
    term,             # e.g., "Term 1"
    components,       # Text: one per line (e.g., "Tuition: 15000")
    total_amount,     # Decimal: sum of all components
    created_by,       # User who created
    created_at        # Timestamp
)
```

### FeeInvoice
Represents a single invoice for a payer.

```python
FeeInvoice(
    school,             # ForeignKey to School
    structure,          # Optional ForeignKey to FeeStructure
    payer_name,         # Name of payer
    invoice_number,     # Auto-generated unique ID
    description,        # Optional invoice description
    amount,             # Decimal amount
    due_date,           # Optional due date
    status,             # pending, paid, or cancelled
    payment_method,     # mpesa, bank, cash, other
    payment_reference,  # Transaction ID or reference
    paid,               # Boolean flag
    paid_at,            # Timestamp when paid
    created_by,         # User who created
    generated_at        # Creation timestamp
)
```

## URLs

| URL Pattern | View | Purpose |
|---|---|---|
| `/fees/` | fees_dashboard | Main fees dashboard |
| `/fees/structures/new/` | create_fee_structure | Create new fee structure |
| `/fees/invoices/new/` | create_invoice | Create new invoice |
| `/fees/invoices/<id>/` | invoice_detail | View invoice details |
| `/fees/invoices/<id>/receipt/` | invoice_receipt | Print professional receipt |
| `/fees/invoices/<id>/pay/` | record_payment | Record payment for invoice |

## Usage Examples

### For Bursars/Administrators

#### 1. Create a Fee Structure
1. Go to **Fees Dashboard** → **New Fee Structure**
2. Select school and term
3. Add fee components (one per line):
   ```
   Tuition: 15000
   Boarding: 8000
   Lab Fee: 1500
   Activity Fee: 500
   ```
4. Enter total amount: 25000
5. Save structure

#### 2. Create an Invoice
1. Go to **Fees Dashboard** → **New Invoice**
2. Select fee structure (auto-fills amount)
3. Enter payer name (student name or guardian)
4. Add optional description
5. Set due date
6. Choose payment method
7. Create invoice

#### 3. Record Payment
1. Go to invoice detail
2. Click **Record Payment**
3. Select payment method
4. Enter payment reference (M-Pesa code, bank ref, etc.)
5. Click **Mark as Paid**
6. System generates receipt automatically

#### 4. Generate Receipt
1. Go to invoice detail
2. Click **Print Receipt** or **View Receipt**
3. Professional receipt displays with:
   - School header and logo
   - Invoice details
   - Amount highlighted
   - Payment status
   - School watermark
4. Print or export as PDF

### For Students/Parents
- View invoices (if permitted)
- Download receipts
- Track payment status
- See payment reference

## Configuration

### Role-Based Access
Edit `fees/views.py` to customize role access:
```python
def _can_manage_fees(user):
    return user.is_superuser or getattr(user, 'role', None) in ['principal', 'dos', 'bursar']
```

### Receipt Customization
Edit `brainet/templates/fees/receipt.html` to:
- Change colors (update CSS variables)
- Adjust watermark style
- Modify header layout
- Change footer text

### Payment Methods
Update `FeeInvoice.PAYMENT_METHOD_CHOICES` in `fees/models.py`:
```python
PAYMENT_METHOD_CHOICES = [
    ('bank', 'Bank Transfer'),
    ('mpesa', 'M-Pesa'),
    ('cash', 'Cash'),
    ('other', 'Other'),
]
```

## API Responses

### Fees Dashboard
Returns:
- Fee structures for school
- Recent invoices with status
- Statistics (total, paid, pending, overdue)

### Invoice Detail
Returns:
- Full invoice information
- Payment status
- Option to record payment
- Link to receipt

### Receipt
Returns:
- Professional HTML receipt
- Print-friendly CSS
- School branding
- Payment confirmation

## Database Queries

### Get unpaid invoices for a school:
```python
unpaid = FeeInvoice.objects.filter(school=school, paid=False)
```

### Get overdue invoices:
```python
today = timezone.now().date()
overdue = FeeInvoice.objects.filter(due_date__lt=today, paid=False)
```

### Calculate total fees for a term:
```python
total = FeeStructure.objects.filter(school=school, term='Term 1').values('total_amount').aggregate(Sum('total_amount'))
```

## Admin Panel

Access Django admin at `/admin/`:
- Manage fee structures
- View all invoices
- Filter by school, status, payment method
- Export reports

## Common Issues

### Invoice number not generating
- Ensure `save()` is called
- Check UUID generation is working

### Receipt not showing school logo
- Verify logo is uploaded to school
- Check Cloudinary settings if using cloud storage

### Payment reference not saving
- Ensure payment_reference field has value
- Check form submission

### Permission denied errors
- Verify user role is correct
- Check school assignment for non-superusers

## Future Enhancements

- [ ] Bulk invoice generation
- [ ] Automated payment reminders (email/SMS)
- [ ] Payment plans (installments)
- [ ] Integration with payment gateways (Daraja, Stripe)
- [ ] Receipt templates by school
- [ ] Financial reports and analytics
- [ ] Multi-currency support
- [ ] Discount/scholarship management
- [ ] Invoice tracking by student
- [ ] Parent portal integration

## Support
For issues or questions, contact system admin or raise issue on GitHub.
