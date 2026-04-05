def mask_email(email: str) -> str:
    try:
        local, domain = email.split("@")
    except ValueError:
        return "***"

    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[:2] + "***" + local[-1]

    domain_parts = domain.split(".")
    
    if len(domain_parts) >= 2:
        name = domain_parts[0]
        tld = ".".join(domain_parts[1:])

        if len(name) <= 2:
            masked_domain = name[0] + "***"
        else:
            masked_domain = name[:2] + "***"

        masked_domain = f"{masked_domain}.{tld}"
    else:
        masked_domain = "***"

    return f"{masked_local}@{masked_domain}"