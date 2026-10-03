import io
import os
from datetime import datetime
from flask import Flask, jsonify, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from twilio.rest import Client

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///enterprise_logistics.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== TWILIO CREDENTIALS ====================
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'your_account_sid_here')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'your_auth_token_here')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '+1234567890')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

# ==================== DATABASE MODELS ====================

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    category = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    gstin = db.Column(db.String(30), nullable=True)
    status = db.Column(db.String(20), default="Active")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "contact": self.contact,
            "email": self.email,
            "phone": self.phone or "N/A",
            "category": self.category,
            "address": self.address or "N/A",
            "gstin": self.gstin or "N/A",
            "status": self.status
        }

class DeliveryPartner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(120), nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    vehicle_no = db.Column(db.String(30), nullable=False)
    service_type = db.Column(db.String(50), default="Express Cargo")
    status = db.Column(db.String(20), default="Available")

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "driver_name": self.driver_name,
            "phone": self.phone,
            "vehicle_no": self.vehicle_no,
            "service_type": self.service_type,
            "status": self.status
        }

class VendorBill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_no = db.Column(db.String(50), unique=True, nullable=False)
    vendor_name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="UNPAID")

    def to_dict(self):
        return {
            "id": self.id,
            "bill_no": self.bill_no,
            "vendor_name": self.vendor_name,
            "total_amount": self.amount,
            "due_amount": max(0.0, self.amount - self.paid_amount),
            "status": self.status
        }

class PaymentTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_no = db.Column(db.String(50), nullable=False)
    vendor_name = db.Column(db.String(120), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_mode = db.Column(db.String(30), nullable=False)
    transaction_ref = db.Column(db.String(100), nullable=False)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)

class Parcel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(50), unique=True, nullable=False)
    vendor_name = db.Column(db.String(120), nullable=False)
    partner_name = db.Column(db.String(120), default="Express Cargo")
    destination = db.Column(db.String(150), nullable=False)
    current_location = db.Column(db.String(150), default="Central Hub")
    lat = db.Column(db.Float, default=21.1904)
    lng = db.Column(db.Float, default=81.2849)
    status = db.Column(db.String(30), default="In-Transit")

    def to_dict(self):
        return {
            "id": self.id,
            "tracking_id": self.tracking_id,
            "vendor_name": self.vendor_name,
            "partner_name": self.partner_name,
            "destination": self.destination,
            "current_location": self.current_location,
            "lat": self.lat,
            "lng": self.lng,
            "status": self.status
        }

# Initial Data Seeding
with app.app_context():
    db.create_all()
    if Vendor.query.count() == 0:
        v1 = Vendor(name="Acme Raw Materials", contact="John Doe", email="john@acme.com", phone="+919876543210", category="Packaging", address="Raipur Industrial Zone", gstin="22AAAAA0000A1Z5")
        v2 = Vendor(name="Global Freight Logistics", contact="Jane Smith", email="jane@global.com", phone="+919876543211", category="Shipping", address="Bhilai Transport Nagar", gstin="22BBBBB1111B1Z2")
        db.session.add_all([v1, v2])

    if DeliveryPartner.query.count() == 0:
        dp1 = DeliveryPartner(company_name="Blue Dart Express", driver_name="Ramesh Kumar", phone="+919123456789", vehicle_no="CG-07-AB-1234", service_type="Air Express")
        dp2 = DeliveryPartner(company_name="Delhivery Freight", driver_name="Suresh Verma", phone="+919826112233", vehicle_no="CG-04-XY-9876", service_type="Surface Cargo")
        db.session.add_all([dp1, dp2])

    if VendorBill.query.count() == 0:
        b1 = VendorBill(bill_no="INV-2026-001", vendor_name="Acme Raw Materials", amount=15000.0, paid_amount=0.0, status="UNPAID")
        b2 = VendorBill(bill_no="INV-2026-002", vendor_name="Global Freight Logistics", amount=28500.0, paid_amount=10000.0, status="PARTIAL")
        db.session.add_all([b1, b2])

    if Parcel.query.count() == 0:
        p1 = Parcel(tracking_id="TRK-1001", vendor_name="Acme Raw Materials", partner_name="Blue Dart Express", destination="Raipur Hub", current_location="Raipur Logistics Hub", lat=21.2514, lng=81.6296, status="In-Transit")
        p2 = Parcel(tracking_id="TRK-1002", vendor_name="Global Freight Logistics", partner_name="Delhivery Freight", destination="Bhilai Cargo Center", current_location="Durg Hub", lat=21.1904, lng=81.2849, status="Out for Delivery")
        db.session.add_all([p1, p2])

    db.session.commit()

# ==================== REST ROUTE ENDPOINTS ====================

@app.route('/')
def home():
    return render_template('index.html')

# --- VENDOR APIS ---
@app.route('/api/vendors', methods=['GET'])
def get_vendors():
    vendors = Vendor.query.all()
    return jsonify([v.to_dict() for v in vendors])

@app.route('/api/vendors', methods=['POST'])
def add_vendor():
    data = request.json
    v = Vendor(
        name=data['name'],
        contact=data.get('contact', 'N/A'),
        email=data['email'],
        phone=data.get('phone', 'N/A'),
        category=data.get('category', 'General'),
        address=data.get('address', 'N/A'),
        gstin=data.get('gstin', 'N/A'),
        status="Active"
    )
    db.session.add(v)
    db.session.commit()
    return jsonify(v.to_dict()), 201

@app.route('/api/vendors/<int:vendor_id>', methods=['DELETE'])
def delete_vendor(vendor_id):
    vendor = Vendor.query.get(vendor_id)
    if vendor:
        db.session.delete(vendor)
        db.session.commit()
        return jsonify({"message": "Vendor removed successfully"}), 200
    return jsonify({"error": "Vendor not found"}), 404

# --- DELIVERY PARTNER APIS ---
@app.route('/api/delivery-partners', methods=['GET'])
def get_delivery_partners():
    partners = DeliveryPartner.query.all()
    return jsonify([p.to_dict() for p in partners])

@app.route('/api/delivery-partners', methods=['POST'])
def add_delivery_partner():
    data = request.json
    dp = DeliveryPartner(
        company_name=data['company_name'],
        driver_name=data['driver_name'],
        phone=data['phone'],
        vehicle_no=data['vehicle_no'],
        service_type=data.get('service_type', 'Express Cargo')
    )
    db.session.add(dp)
    db.session.commit()
    return jsonify(dp.to_dict()), 201

# --- FINANCIAL BILLS & DUES CLEARANCE APIS ---
@app.route('/api/bills/outstanding', methods=['GET'])
def get_outstanding_bills():
    bills = VendorBill.query.filter(VendorBill.status != 'PAID').all()
    return jsonify([b.to_dict() for b in bills])

@app.route('/api/bills/pay', methods=['POST'])
def process_payment():
    data = request.json
    bill_no = data.get('bill_no')
    pay_amount = float(data.get('amount'))
    pay_mode = data.get('payment_mode', 'UPI / QR Code')
    txn_ref = f"TXN-{int(datetime.utcnow().timestamp())}"

    bill = VendorBill.query.filter_by(bill_no=bill_no).first()
    if not bill:
        return jsonify({"error": "Bill not found"}), 404

    bill.paid_amount += pay_amount
    if (bill.amount - bill.paid_amount) <= 0:
        bill.status = "PAID"
    else:
        bill.status = "PARTIAL"

    txn = PaymentTransaction(
        bill_no=bill_no,
        vendor_name=bill.vendor_name,
        amount_paid=pay_amount,
        payment_mode=pay_mode,
        transaction_ref=txn_ref
    )
    db.session.add(txn)
    db.session.commit()
    return jsonify({"message": "Payment Settled", "txn_ref": txn_ref, "status": bill.status}), 200

# --- AUTO-GENERATED GST PDF RECEIPT API ---
@app.route('/api/receipt/download/<string:txn_ref>', methods=['GET'])
def generate_pdf_receipt(txn_ref):
    txn = PaymentTransaction.query.filter_by(transaction_ref=txn_ref).first()
    if not txn:
        return jsonify({"error": "Transaction record not found"}), 404

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(100, 750, "ENTERPRISE LOGISTICS PORTAL")
    p.setFont("Helvetica", 10)
    p.drawString(100, 735, "Official Payment Settlement & GST Tax Receipt")
    p.line(100, 725, 500, 725)

    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, 690, f"Transaction Ref: {txn.transaction_ref}")
    p.setFont("Helvetica", 11)
    p.drawString(100, 665, f"Date: {txn.paid_at.strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawString(100, 645, f"Invoice Bill No: {txn.bill_no}")
    p.drawString(100, 625, f"Vendor Name: {txn.vendor_name}")
    p.drawString(100, 605, f"Payment Channel: {txn.payment_mode}")
    p.line(100, 585, 500, 585)

    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 550, f"Total Amount Cleared: INR {txn.amount_paid:,.2f}")
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(100, 520, "Payment Status: CLEARED & VERIFIED")

    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Receipt_{txn.transaction_ref}.pdf", mimetype='application/pdf')

# --- PARCEL & GPS MAP ENDPOINTS ---
@app.route('/api/parcels', methods=['GET'])
def get_parcels():
    parcels = Parcel.query.all()
    return jsonify([p.to_dict() for p in parcels])

@app.route('/api/parcels/update-status', methods=['POST'])
def update_parcel_status():
    data = request.json
    trk_id = data.get('tracking_id')
    status = data.get('status')
    phone = data.get('phone_number')
    channel = data.get('channel', 'both')

    parcel = Parcel.query.filter_by(tracking_id=trk_id).first()
    if parcel:
        parcel.status = status
        db.session.commit()

    msg = f"📦 Logistics Alert\nParcel: {trk_id}\nStatus: {status}\nTrack Live: http://127.0.0.1:5000/"
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        if channel in ['sms', 'both'] and phone:
            client.messages.create(body=msg, from_=TWILIO_PHONE_NUMBER, to=phone)
        if channel in ['whatsapp', 'both'] and phone:
            client.messages.create(body=msg, from_=TWILIO_WHATSAPP_NUMBER, to=f"whatsapp:{phone}")
    except Exception:
        pass

    return jsonify({"message": "Parcel status updated & alerts dispatched"}), 200

@app.route('/api/qr/generate/<string:tracking_id>', methods=['GET'])
def generate_qr(tracking_id):
    data = f"http://127.0.0.1:5000/?track={tracking_id}"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')

# --- AI ASSISTANT ENDPOINT ---
@app.route('/api/ai-assistant', methods=['POST'])
def ai_assistant():
    query = request.json.get('query', '').lower()
    if 'due' in query or 'pending' in query or 'unpaid' in query:
        unpaid = VendorBill.query.filter(VendorBill.status != 'PAID').all()
        due_tot = sum([b.amount - b.paid_amount for b in unpaid])
        reply = f"System Audit: {len(unpaid)} unpaid vendor bills found. Total outstanding balance is INR {due_tot:,.2f}."
    elif 'track' in query or 'parcel' in query or 'location' in query or 'map' in query:
        reply = "Parcels are being tracked live on the OpenStreetMap view. You can also scan any box QR label via the webcam scanner."
    else:
        reply = "I am your AI Supply Chain Assistant. Ask me about pending vendor dues, live parcel locations, or delivery partners!"
    return jsonify({"reply": reply})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)