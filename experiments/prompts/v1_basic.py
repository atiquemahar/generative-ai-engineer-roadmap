# Minimal prompt - baseline

SYSTEM_PROMPT_V1 = """
Extract complaint information from the customer message.
Return JSON with: intent, priority, customer_id, order_id, requested_action, missing_fields, confidence
intent options: shipment_delay, refund_request, product_defect, account_issue, general_inquiry
priority options: low, medium, high
confidence: low, medium, high
"""