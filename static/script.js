let map, markersGroup;

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadVendors();
    loadDeliveryPartners();
    loadOutstandingDues();

    document.getElementById('addVendorForm').addEventListener('submit', handleAddVendor);
    document.getElementById('addPartnerForm').addEventListener('submit', handleAddPartner);
    document.getElementById('notifyForm').addEventListener('submit', sendDispatchNotification);
});

function switchView(viewName, event) {
    if (event) event.preventDefault();
    document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.page-view').forEach(el => el.classList.remove('active'));

    const activeLink = Array.from(document.querySelectorAll('.nav-link'))
        .find(el => el.getAttribute('onclick').includes(viewName));
    if (activeLink) activeLink.classList.add('active');

    const targetView = document.getElementById(`view-${viewName}`);
    if (targetView) targetView.classList.add('active');

    if (viewName === 'tracking') setTimeout(() => map.invalidateSize(), 200);
}

// LOAD VENDORS & RENDER TABLE WITH REMOVE BUTTON
async function loadVendors() {
    const res = await fetch('/api/vendors');
    const vendors = await res.json();
    const tbody = document.getElementById('vendorListTableBody');
    tbody.innerHTML = '';

    vendors.forEach(v => {
        tbody.innerHTML += `
            <tr>
                <td>#${v.id}</td>
                <td><strong>${v.name}</strong><br><small style="color:#64748b;">${v.category}</small></td>
                <td>${v.contact}</td>
                <td>${v.phone}<br><small>${v.email}</small></td>
                <td><code>${v.gstin}</code></td>
                <td>${v.address}</td>
                <td class="text-right">
                    <button class="btn btn-delete" style="padding: 0.38rem 0.65rem; font-size:0.8rem;" onclick="removeVendor(${v.id})">
                        Remove
                    </button>
                </td>
            </tr>
        `;
    });
}

// ADD NEW VENDOR (DETAILED)
async function handleAddVendor(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('vName').value,
        contact: document.getElementById('vContact').value,
        email: document.getElementById('vEmail').value,
        phone: document.getElementById('vPhone').value,
        category: document.getElementById('vCategory').value,
        gstin: document.getElementById('vGstin').value,
        address: document.getElementById('vAddress').value
    };

    const res = await fetch('/api/vendors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        alert('Vendor Profile Saved Successfully!');
        document.getElementById('addVendorForm').reset();
        loadVendors();
    }
}

// REMOVE / DELETE VENDOR
async function removeVendor(vendorId) {
    if (!confirm(`Are you sure you want to remove Vendor #${vendorId}?`)) return;

    const res = await fetch(`/api/vendors/${vendorId}`, {
        method: 'DELETE'
    });

    if (res.ok) {
        alert('Vendor removed from database.');
        loadVendors();
    } else {
        alert('Failed to remove vendor.');
    }
}

function filterVendorTable() {
    const input = document.getElementById('vendorSearchInput').value.toLowerCase();
    const rows = document.getElementById('vendorListTableBody').getElementsByTagName('tr');
    for (let row of rows) {
        row.style.display = row.textContent.toLowerCase().includes(input) ? '' : 'none';
    }
}

// DELIVERY PARTNER MANAGEMENT
async function loadDeliveryPartners() {
    const res = await fetch('/api/delivery-partners');
    const partners = await res.json();
    const tbody = document.getElementById('partnerTableBody');
    tbody.innerHTML = '';

    partners.forEach(p => {
        tbody.innerHTML += `
            <tr>
                <td>#${p.id}</td>
                <td><strong>${p.company_name}</strong></td>
                <td>${p.driver_name}</td>
                <td>${p.phone}</td>
                <td><code>${p.vehicle_no}</code></td>
                <td><span class="badge" style="background:#dcfce7; color:#15803d;">${p.status}</span></td>
            </tr>
        `;
    });
}

async function handleAddPartner(e) {
    e.preventDefault();
    const payload = {
        company_name: document.getElementById('dpCompany').value,
        driver_name: document.getElementById('dpDriver').value,
        phone: document.getElementById('dpPhone').value,
        vehicle_no: document.getElementById('dpVehicle').value
    };

    const res = await fetch('/api/delivery-partners', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        alert('Delivery Partner Added!');
        document.getElementById('addPartnerForm').reset();
        loadDeliveryPartners();
    }
}

// LEAFLET MAP & OUTSTANDING DUES
async function initMap() {
    map = L.map('map').setView([21.1904, 81.2849], 7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    markersGroup = L.layerGroup().addTo(map);
    loadMapParcels();
}

async function loadMapParcels() {
    markersGroup.clearLayers();
    const res = await fetch('/api/parcels');
    const parcels = await res.json();
    parcels.forEach(p => {
        L.marker([p.lat, p.lng]).addTo(markersGroup)
            .bindPopup(`<b>${p.tracking_id}</b><br>Vendor: ${p.vendor_name}<br>Partner: ${p.partner_name}<br>Status: ${p.status}`);
    });
}

async function loadOutstandingDues() {
    const res = await fetch('/api/bills/outstanding');
    const bills = await res.json();
    const tbody = document.getElementById('duesTableBody');
    tbody.innerHTML = '';

    if (bills.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:2rem;">No Outstanding Dues! All Bills Cleared.</td></tr>';
        return;
    }

    bills.forEach(b => {
        tbody.innerHTML += `
            <tr>
                <td><strong>${b.bill_no}</strong></td>
                <td>${b.vendor_name}</td>
                <td>₹${b.total_amount.toLocaleString()}</td>
                <td><strong style="color:#ef4444;">₹${b.due_amount.toLocaleString()}</strong></td>
                <td><span class="badge">${b.status}</span></td>
                <td class="text-right">
                    <button class="btn btn-primary" onclick="openPaymentModal('${b.bill_no}', '${b.vendor_name}', ${b.due_amount})">
                        Pay Dues
                    </button>
                </td>
            </tr>
        `;
    });
}

// PAYMENT MODAL & AUTOMATIC DUES CLEARANCE
let activeBillNo = '';
function openPaymentModal(billNo, vendor, dueAmount) {
    activeBillNo = billNo;
    document.getElementById('modalBillNo').textContent = billNo;
    document.getElementById('modalVendor').textContent = vendor;
    document.getElementById('modalDueAmount').textContent = dueAmount;
    document.getElementById('payInputAmount').value = dueAmount;
    document.getElementById('paymentModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('paymentModal').style.display = 'none';
}

async function submitPayment() {
    const amount = document.getElementById('payInputAmount').value;
    const mode = document.getElementById('payMethod').value;

    const res = await fetch('/api/bills/pay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bill_no: activeBillNo, amount: amount, payment_mode: mode })
    });

    const data = await res.json();
    if (res.ok) {
        alert(`Payment Successful!\nTxn Ref: ${data.txn_ref}`);
        closeModal();
        loadOutstandingDues(); // Refresh table: fully paid bill automatically disappears

        if (confirm('Download PDF Settlement Receipt?')) {
            window.location.href = `/api/receipt/download/${data.txn_ref}`;
        }
    }
}

// QR CODE & WEBCAM SCANNER
function displayQRCode() {
    const trackId = document.getElementById('qrTrackInput').value.trim();
    if (!trackId) return;
    document.getElementById('qrImage').src = `/api/qr/generate/${trackId}`;
    document.getElementById('qrDisplayContainer').style.display = 'block';
}

let videoStream = null, scanning = false;
async function startCameraScanner() {
    const video = document.getElementById('webcamVideo');
    try {
        videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        video.srcObject = videoStream;
        video.style.display = 'inline-block';
        document.getElementById('stopScanBtn').style.display = 'inline-block';
        video.play();
        scanning = true;
        requestAnimationFrame(scanQRCodeFrame);
    } catch (err) { alert("Camera access denied: " + err.message); }
}

function scanQRCodeFrame() {
    if (!scanning) return;
    const video = document.getElementById('webcamVideo');
    const canvasElement = document.getElementById('qrCanvas');
    const canvas = canvasElement.getContext('2d');

    if (video.readyState === video.HAVE_ENOUGH_DATA) {
        canvasElement.height = video.videoHeight;
        canvasElement.width = video.videoWidth;
        canvas.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);

        const imageData = canvas.getImageData(0, 0, canvasElement.width, canvasElement.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height);

        if (code) {
            document.getElementById('scannedResult').innerHTML = `✅ Scanned QR: <strong>${code.data}</strong>`;
            stopCameraScanner();
            return;
        }
    }
    if (scanning) requestAnimationFrame(scanQRCodeFrame);
}

function stopCameraScanner() {
    scanning = false;
    if (videoStream) videoStream.getTracks().forEach(track => track.stop());
    document.getElementById('webcamVideo').style.display = 'none';
    document.getElementById('stopScanBtn').style.display = 'none';
}

// TWILIO DISPATCH NOTIFICATIONS
async function sendDispatchNotification(e) {
    e.preventDefault();
    const payload = {
        tracking_id: document.getElementById('notifyTrackId').value,
        phone_number: document.getElementById('notifyPhone').value,
        status: document.getElementById('notifyStatus').value,
        channel: document.getElementById('notifyChannel').value
    };

    const res = await fetch('/api/parcels/update-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res.ok) alert('Dispatch alert sent successfully!');
}

// AI ASSISTANT CHATBOT
function toggleAIChat() {
    const box = document.getElementById('aiChatWindow');
    box.style.display = box.style.display === 'none' ? 'flex' : 'none';
}

async function sendAIMessage() {
    const input = document.getElementById('aiInputText');
    const msg = input.value.trim();
    if (!msg) return;

    const chatBox = document.getElementById('aiChatMessages');
    chatBox.innerHTML += `<div class="ai-msg user">${msg}</div>`;
    input.value = '';

    const res = await fetch('/api/ai-assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: msg })
    });
    const data = await res.json();

    chatBox.innerHTML += `<div class="ai-msg bot">${data.reply}</div>`;
    chatBox.scrollTop = chatBox.scrollHeight;
}

// EXPORT TO EXCEL (CSV)
async function exportToCSV(type) {
    const res = await fetch('/api/bills/outstanding');
    const data = await res.json();
    let csv = 'Bill No,Vendor Name,Total Amount,Due Amount,Status\n';
    data.forEach(b => {
        csv += `"${b.bill_no}","${b.vendor_name}",${b.total_amount},${b.due_amount},"${b.status}"\n`;
    });
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Outstanding_Vendor_Dues.csv';
    a.click();
}
