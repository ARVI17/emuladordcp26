// Game tokens are ordinary vocabulary. Credential labels and credential-shaped
// values are sensitive even when their value is short or uses a different label.
export const sensitiveText = /password|contrase[nñ]a|cookie|bearer|secret|captcha|\bmfa\b|\botp\b|verification|verificaci[oó]n|iniciar sesi[oó]n|sign\s?in|log\s?in|checkout|payment|pago|recovery|recuperaci[oó]n|\b(?:access|refresh|session|auth(?:entication)?|id|api|csrf)[_ -]*tokens?\b|\btokens?\s*[:=]|\btoken\s+(?:de\s+)?(?:acceso|sesi[oó]n|autenticaci[oó]n|seguridad)\b|\S+@\S+|https?:|[A-Za-z0-9_-]{32,}/i
