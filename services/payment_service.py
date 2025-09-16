from uuid import uuid4

def create_order(event_id: str, amount: int):
    return {
        "orderId": "order_" + uuid4().hex[:12],
        "eventId": event_id,
        "amount": amount,
        "currency": "INR"
    }
