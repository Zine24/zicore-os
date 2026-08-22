"""
ZICORE System - Crypto Payment Module
Handles cryptocurrency payments for services (BTC, ETH, ZTN).
"""
import json
import hashlib
import time
import uuid
import os
from pathlib import Path
from typing import Optional

PAYMENTS_FILE = Path(__file__).parent.parent / "data" / "config" / "crypto_payments.json"

# Service pricing (ZNT tokens or USD equivalent)
SERVICES = {
    "mail_basic": {
        "name": "Mail Básico",
        "description": "1 buzón @zicore.space o @zinemotion.com.mx",
        "price_ztn": 10,
        "price_btc": 0.00015,
        "price_eth": 0.003,
        "price_usd": 5,
        "duration_days": 30,
    },
    "mail_pro": {
        "name": "Mail Pro",
        "description": "5 buzones + dominio personalizado",
        "price_ztn": 50,
        "price_btc": 0.00075,
        "price_eth": 0.015,
        "price_usd": 25,
        "duration_days": 30,
    },
    "mail_ultimate": {
        "name": "Mail Ultimate",
        "description": "Ilimitado + prioridad + soporte",
        "price_ztn": 200,
        "price_btc": 0.003,
        "price_eth": 0.06,
        "price_usd": 100,
        "duration_days": 30,
    },
    "storage_10gb": {
        "name": "Almacenamiento 10GB",
        "description": "10GB adicionales para archivos",
        "price_ztn": 5,
        "price_btc": 0.000075,
        "price_eth": 0.0015,
        "price_usd": 2.5,
        "duration_days": 30,
    },
    "zicore_api": {
        "name": "API Access",
        "description": "Acceso a APIs de ZICORE",
        "price_ztn": 100,
        "price_btc": 0.0015,
        "price_eth": 0.03,
        "price_usd": 50,
        "duration_days": 30,
    },
}

# Deposit addresses (simplified - in production use HD wallets)
DEPOSIT_ADDRESSES = {
    "btc": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "eth": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD3e",
    "ztn": "ZTNCORE1qyf5n7m8x9p2w3e4r5t6y7u8i9o0p",
}

def _load_payments() -> dict:
    try:
        if PAYMENTS_FILE.exists():
            with open(PAYMENTS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"payments": [], "config": DEPOSIT_ADDRESSES}

def _save_payments(data: dict):
    PAYMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PAYMENTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def create_payment(service_id: str, user_email: str, crypto: str = "ztn") -> dict:
    """Create a new payment request for a service."""
    if service_id not in SERVICES:
        return {"error": "Invalid service"}
    
    service = SERVICES[service_id]
    crypto = crypto.lower()
    
    price_key = f"price_{crypto}"
    if price_key not in service:
        return {"error": f"Unsupported cryptocurrency: {crypto}"}
    
    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    amount = service[price_key]
    address = DEPOSIT_ADDRESSES.get(crypto, "")
    
    payment = {
        "id": payment_id,
        "service": service_id,
        "service_name": service["name"],
        "user_email": user_email,
        "crypto": crypto.upper(),
        "amount": amount,
        "address": address,
        "status": "pending",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + 3600)),
        "duration_days": service["duration_days"],
        "price_usd": service["price_usd"],
    }
    
    data = _load_payments()
    data["payments"].append(payment)
    _save_payments(data)
    
    return payment

def get_payment(payment_id: str) -> Optional[dict]:
    """Get payment details."""
    data = _load_payments()
    for p in data["payments"]:
        if p["id"] == payment_id:
            return p
    return None

def confirm_payment(payment_id: str) -> dict:
    """Manually confirm a payment (admin action)."""
    data = _load_payments()
    for p in data["payments"]:
        if p["id"] == payment_id:
            p["status"] = "confirmed"
            p["confirmed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _save_payments(data)
            return {"status": "ok", "payment": p}
    return {"error": "Payment not found"}

def get_user_payments(user_email: str) -> list:
    """Get all payments for a user."""
    data = _load_payments()
    return [p for p in data["payments"] if p.get("user_email") == user_email]

def get_all_payments() -> list:
    """Get all payments (admin)."""
    data = _load_payments()
    return data.get("payments", [])

def get_stats() -> dict:
    """Get payment statistics."""
    data = _load_payments()
    payments = data.get("payments", [])
    total = len(payments)
    pending = sum(1 for p in payments if p["status"] == "pending")
    confirmed = sum(1 for p in payments if p["status"] == "confirmed")
    revenue_ztn = sum(p["amount"] for p in payments if p["status"] == "confirmed" and p["crypto"] == "ZTN")
    revenue_usd = sum(p.get("price_usd", 0) for p in payments if p["status"] == "confirmed")
    
    return {
        "total_payments": total,
        "pending": pending,
        "confirmed": confirmed,
        "revenue_ztn": revenue_ztn,
        "revenue_usd": revenue_usd,
    }

def get_services() -> dict:
    """Get available services and pricing."""
    return SERVICES
