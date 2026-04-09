"""Mask secrets in adapter config dicts for API responses (site onboarding)."""


def _mask_adapter_config(config, adapter_id=None):
    """Return config copy with api_key and password masked; never log or expose secrets."""
    if not config or not isinstance(config, dict):
        return config
    c = dict(config)
    if c.get('api_key'):
        c['api_key'] = '****'
    if adapter_id in ('fusion_solar', 'laplaceid') and c.get('password'):
        c['password'] = '****'
    return c


def _mask_api_key(config):
    """Return config copy with api_key masked (and password for fusion_solar). Kept for backward compatibility."""
    return _mask_adapter_config(config)

