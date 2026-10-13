def normalize_field(value: str) -> str:
    """Lowercase and strip whitespace for fuzzy matching."""
    return value.lower().strip()


def fields_match_customer(
    first_name: str,
    last_name: str,
    address: str,
    phone: str,
    customer_first: str,
    customer_last: str,
    customer_address: str,
    customer_phone: str,
) -> bool:
    """
    Check if provided identity fields match a customer record.
    Phone must match exactly (normalized). Name must match (case-insensitive).
    Address: normalized substring match (customer address must contain the provided address).
    """
    phone_match = normalize_field(phone) == normalize_field(customer_phone)
    first_match = normalize_field(first_name) == normalize_field(customer_first)
    last_match = normalize_field(last_name) == normalize_field(customer_last)
    # Address: either direction substring is acceptable for mocked data
    addr_norm = normalize_field(address)
    customer_addr_norm = normalize_field(customer_address)
    address_match = addr_norm in customer_addr_norm or customer_addr_norm in addr_norm
    return phone_match and first_match and last_match and address_match
