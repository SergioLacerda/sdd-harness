# 🔒 Security Model

**Status:** ✅ Complete
**Version:** 1.0
**Last Updated:** 2026-04-19
**Applicable To:** All [PROJECT_NAME] projects (100% inherited from CANONICAL/)

---

## 🎯 Overview

Complete security model defining threat protection, authentication, authorization, data protection, and incident response for all projects in the SPEC framework.

**Security is MANDATORY** — Every project must implement all requirements in this document.

**Framework compliance:** All security decisions must align with:
- [Architecture Specification](./architecture.md) (Principles)
- [Performance Specification](./performance.md) (SLOs apply to security operations)
- [ADR-002: Async-First](../../decisions/ADR-002-async-first-no-blocking.md) (all security operations must be non-blocking)

---

## 📋 Part 1: Threat Model

### 1.1 Asset Identification

**Critical Assets:**
1. **User Data** — Campaign state, player information, preferences
2. **LLM Credentials** — API keys (OpenAI, local endpoints)
3. **Vector Index** — Narrative embeddings (intellectual property)
4. **API Keys** — All authentication tokens
5. **Audit Logs** — Event history, debugging information

**Sensitive Assets:**
1. Player behavior patterns
2. Campaign narratives (potentially copyrighted)
3. Rate limiting state
4. Session data

**Infrastructure:**
1. API servers
2. Storage (JSON files, databases)
3. Vector index
4. LLM endpoints

---

### 1.2 Attack Surface Mapping

**Primary Entry Points:**
```
HTTP API → API Security (see authentication/authorization section below)
Discord Bot → interfaces/discord/
CLI → interfaces/cli/
```

**Trust Boundaries:**
```
         [External Users]
                |
        [API Gateway] ← Trust boundary #1
                |
         [Services]
                |
        [Data Layer] ← Trust boundary #2
                |
    [Storage/Vector Index]
```

**Potential Attack Vectors:**

| Attack Vector | Risk | Mitigation |
|---|---|---|
| SQL Injection | HIGH | Input validation, parameterized queries (when DB used) |
| LLM Prompt Injection | HIGH | Strict input validation on user narratives |
| Token Forgery | HIGH | Cryptographic signatures (JWT HS256+) |
| Rate Limit Bypass | MEDIUM | Distributed rate limiting with shared state |
| Unauthorized Access | MEDIUM | RBAC with explicit deny default |
| Data Exfiltration | HIGH | Encryption at rest + in transit |
| DDoS | MEDIUM | Circuit breakers, backpressure (see performance.md) |
| Timing Attacks | LOW | Constant-time comparison for secrets |

---

### 1.3 OWASP Top 10 Mitigation

**A01:2021 – Broken Access Control**
- ✅ Implement RBAC (Role-Based Access Control)
- ✅ Explicit allow/deny lists (deny-by-default)
- ✅ Campaign isolation (each campaign has its own container)
- ✅ Audit log all privilege escalation attempts

**A02:2021 – Cryptographic Failures**
- ✅ Encryption in transit (HTTPS/TLS 1.2+)
- ✅ Encryption at rest (AES-256 for sensitive data)
- ✅ Cryptographically secure random for tokens
- ✅ Never store plaintext secrets

**A03:2021 – Injection**
- ✅ Input validation on all API endpoints (Pydantic)
- ✅ Output encoding (JSON serialization)
- ✅ Parameterized queries when using DB
- ✅ Strict LLM prompt templates (no user concatenation)

**A04:2021 – Insecure Design**
- ✅ Threat model defined (this section)
- ✅ Secure defaults in code
- ✅ Security as architecture requirement
- ✅ Regular security review (quarterly)

**A05:2021 – Security Misconfiguration**
- ✅ No default credentials
- ✅ Minimal permissions principle
- ✅ Security headers enforced (CORS, CSP, X-Frame-Options)
- ✅ Secrets in environment, never in code

**A06:2021 – Vulnerable Components**
- ✅ Dependency scanning (pip-audit)
- ✅ Regular updates (monthly)
- ✅ CVE monitoring
- ✅ Approved dependencies only

**A07:2021 – Authentication Failures**
- ✅ Strong password policy (if applicable)
- ✅ Multi-factor authentication support
- ✅ Session timeout (30min default)
- ✅ Secure token storage (httpOnly cookies)

**A08:2021 – Software Data Integrity Failures**
- ✅ Dependency verification (pip hash checking)
- ✅ Code signing (git commits signed)
- ✅ Immutable event logs (append-only)
- ✅ Checksum verification on downloads

**A09:2021 – Logging & Monitoring Failures**
- ✅ Security audit log (all authentication events)
- ✅ Monitoring for suspicious patterns
- ✅ Alert on repeated failed authentication
- ✅ Log retention (90 days minimum)

**A10:2021 – Server-Side Request Forgery (SSRF)**
- ✅ Whitelist allowed LLM endpoints
- ✅ URL validation (no localhost, 127.0.0.1)
- ✅ Timeout on external requests (30s)
- ✅ No user control over LLM endpoint

---

## 📋 Part 2: Authentication & Authorization

### 2.1 Authentication Protocol

**Status:** Foundation implemented, JWT support ready

**Requirements:**

1. **Token-Based Authentication (OAuth2 + JWT)**
   ```
   Flow:
   1. Client sends credentials
   2. Server verifies (against user database)
   3. Server issues JWT token
   4. Client includes token in Authorization header
   5. Server validates token on each request
   ```

2. **JWT Specifications**
   - Algorithm: HS256 (HMAC) minimum, RS256 (RSA) recommended for services
   - Secret: Environment variable only (never in code)
   - Payload must include:
     - `sub` (subject/user_id)
     - `exp` (expiration timestamp)
     - `iat` (issued at)
     - `role` (user role)
   - Signature: MUST use strong secret (min 32 bytes)

3. **Token Lifetime**
   - Access token: 1 hour (short-lived)
   - Refresh token: 30 days (long-lived, if used)
   - Session timeout: 30 minutes idle

4. **Token Validation Rules**
   ```python
   # Pseudo-code
   def validate_token(token: str) -> dict:
       try:
           payload = jwt.decode(
               token,
               key=SECRET_KEY,  # from env
               algorithms=["HS256"],
           )
           # Check not expired
           if payload["exp"] < time.time():
               raise TokenExpiredError()

           # Check user exists
           user = get_user(payload["sub"])
           if not user:
               raise UserNotFoundError()

           return payload
       except Exception as e:
           raise AuthenticationError(str(e))
   ```

---

### 2.2 Authorization Model (RBAC)

**Role Definitions:**

| Role | Permissions | Use Case |
|------|-------------|----------|
| `admin` | All operations | System management |
| `game_master` | Create campaigns, manage players | Campaign owner |
| `player` | Execute actions in assigned campaign | Player |
| `viewer` | Read-only access | Spectators |
| `system` | Internal system operations | Service-to-service |

**RBAC Rules:**

```python
# Route protection (FastAPI)
@app.get("/campaigns/{id}")
async def get_campaign(
    id: str,
    current_user: User = Depends(get_current_user),
):
    # Check user has permission
    if not has_permission(current_user, "read_campaign", campaign_id=id):
        raise PermissionError(403)

    campaign = fetch_campaign(id)
    return campaign
```

**Permission Matrix:**

| Action | Admin | GM | Player | Viewer |
|--------|-------|----|----|--------|
| Create campaign | ✅ | ✅ | ❌ | ❌ |
| Delete campaign | ✅ | ✅ | ❌ | ❌ |
| Invite player | ✅ | ✅ | ❌ | ❌ |
| Execute action | ✅ | ✅ | ✅ | ❌ |
| View logs | ✅ | ✅ | ✅ | ❌ |
| Read campaign | ✅ | ✅ | ✅ | ✅ |
| Modify config | ✅ | ✅ | ❌ | ❌ |
| Delete user | ✅ | ❌ | ❌ | ❌ |

**Campaign Isolation:**

```python
# Ensure campaign isolation (mandatory)
def get_campaign_for_user(
    campaign_id: str,
    user: User,
) -> Campaign:
    """Get campaign only if user has access"""
    campaign = Campaign.get(campaign_id)

    # Check user is in campaign members
    if user.id not in campaign.members:
        raise AccessDeniedError("User not in campaign")

    # Check user role has permission for this campaign
    user_role = campaign.get_member_role(user.id)
    if not user_role in ["admin", "gm", "player", "viewer"]:
        raise AccessDeniedError("Invalid role")

    return campaign
```

---

### 2.3 Session Management

**Session Rules:**

1. **Creation**
   - Session created on successful authentication
   - Session ID: Cryptographically random (use `secrets.token_urlsafe(32)`)
   - Store in httpOnly cookie (not accessible from JavaScript)

2. **Validation**
   - Every request must have valid session or JWT token
   - Both methods supported (cookies for web, JWT for API)

3. **Termination**
   - Session expires after 30 minutes of inactivity
   - Session terminated on logout
   - Session terminated on password change
   - All sessions terminated on admin request

4. **Storage**
   - Session data: In-memory with optional persistence
   - Session ID: Never log in plaintext
   - Tokens: Never logged at all

---

## 📋 Part 3: Data Protection

### 3.1 Encryption in Transit

**HTTPS/TLS Requirements:**

- Minimum: TLS 1.2 (TLS 1.3 preferred)
- Certificate: Valid and trusted (not self-signed in production)
- All traffic: Must be encrypted
- Mixed content: Not allowed (no HTTP + HTTPS mixing)

**Implementation:**

```python
# FastAPI with HTTPS
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# Force HTTPS in production
if ENV == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

**API Security Headers:**

```python
# Add security headers to all responses
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Prevent XSS
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # HSTS (strict transport security)
    if ENV == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

    return response
```

---

### 3.2 Encryption at Rest

**Sensitive Data Requiring Encryption:**

1. API keys (OpenAI, LLM providers)
2. User credentials (if stored)
3. Private campaign data (if marked sensitive)

**Encryption Standard:**

- Algorithm: AES-256-GCM
- Key Management: Environment variables or key vault
- Initialization Vector (IV): Random per record

**Implementation:**

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

# Load encryption key from environment
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")  # 32 bytes for AES-256

def encrypt_data(plaintext: str) -> str:
    """Encrypt sensitive data"""
    iv = os.urandom(12)  # 96-bit IV for GCM
    cipher = AESGCM(ENCRYPTION_KEY)
    ciphertext = cipher.encrypt(iv, plaintext.encode(), None)

    # Store: iv + ciphertext (both base64)
    import base64
    encrypted = base64.b64encode(iv + ciphertext).decode()
    return encrypted

def decrypt_data(encrypted: str) -> str:
    """Decrypt sensitive data"""
    import base64
    data = base64.b64decode(encrypted)
    iv = data[:12]
    ciphertext = data[12:]

    cipher = AESGCM(ENCRYPTION_KEY)
    plaintext = cipher.decrypt(iv, ciphertext, None)
    return plaintext.decode()
```

---

### 3.3 PII Handling

**Personally Identifiable Information (PII):**

Definition: Any data that can identify a user:
- Email
- User ID
- Username
- Campaign membership
- Player actions/history
- IP address

**PII Protection Rules:**

1. **Collection**
   - Collect minimum necessary only
   - Inform users what data is collected
   - Get explicit consent before processing

2. **Storage**
   - Encrypt PII at rest
   - Store only in secure location
   - Limited access (role-based)

3. **Transmission**
   - Use HTTPS/TLS only
   - Never include PII in URLs or logs
   - Never send PII in error messages

4. **Retention**
   - Default: Delete after 90 days
   - Exceptions: Document why kept longer
   - Audit trail: When PII was accessed/deleted

5. **Deletion**
   - Full deletion: User can request "right to be forgotten"
   - Soft delete: First 90 days, then permanent
   - Verification: Confirm deletion complete

**Implementation:**

```python
# Never log PII
def log_action(user_id: str, action: str):
    """Log user action WITHOUT user_id in message"""
    # ❌ WRONG: log.info(f"User {user_id} performed action")
    # ✅ RIGHT: Log hash instead
    user_hash = hash(user_id)  # One-way hash
    log.info(f"User performed action (id_hash={user_hash})")
```

---

### 3.4 Data Retention Policy

**Default Retention Times:**

| Data Type | Retention | Reason |
|-----------|-----------|--------|
| Audit logs | 90 days | Compliance |
| Session data | 30 days | Security |
| User credentials | Until deletion | Security |
| Campaign events | Indefinite* | Business value |
| PII | 90 days | GDPR/Privacy |
| Temp files | 1 day | Cleanup |
| Error logs | 30 days | Debugging |

*Campaign events can be kept indefinite if user consents

**Cleanup Implementation:**

```python
async def cleanup_old_data():
    """Run daily at 02:00 UTC"""
    # Delete sessions older than 30 days
    Session.delete_before(days=30)

    # Delete audit logs older than 90 days
    AuditLog.delete_before(days=90)

    # Delete PII older than 90 days (without campaign data)
    UserPII.delete_before(days=90)

    # Clean temp files
    cleanup_temp_directory()

    logger.info("Cleanup complete")
```

---

## 📋 Part 4: API Security

### 4.1 Input Validation

**Validation Rules:**

1. **All inputs must be validated**
   - Type check (int, str, bool, etc.)
   - Length check (string max length)
   - Format check (email, UUID, etc.)
   - Range check (numbers min/max)
   - Whitelist check (only allowed values)

2. **Use Pydantic for validation**
   ```python
   from pydantic import BaseModel, Field, validator

   class CreateCampaignRequest(BaseModel):
       name: str = Field(..., min_length=1, max_length=100)
       description: str = Field(max_length=1000)
       max_players: int = Field(default=5, ge=1, le=100)

       @validator("name")
       def name_no_special_chars(cls, v):
           if not v.isalnum() and "_" not in v:
               raise ValueError("Name can only contain alphanumeric and _")
           return v
   ```

3. **Reject invalid input early**
   ```python
   @app.post("/campaigns")
   async def create_campaign(
       req: CreateCampaignRequest,  # Pydantic validates
       user: User = Depends(get_current_user),
   ):
       # At this point, req is guaranteed valid
       campaign = await campaign_service.create(req, user)
       return campaign
   ```

---

### 4.2 Rate Limiting

**Rate Limiting Strategy:**

| Endpoint Type | Limit | Window | Burst |
|---|---|---|---|
| Public (login) | 10 req/min | 1 min | 5 |
| Create action | 50 req/min | 1 min | 20 |
| Read (list) | 100 req/min | 1 min | 50 |
| Generate (LLM) | 5 req/min | 1 min | 3 |
| Admin | Unlimited | N/A | N/A |

**Implementation:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/campaigns")
@limiter.limit("50/minute")
async def create_campaign(
    req: CreateCampaignRequest,
    request: Request,
):
    # Automatically enforced
    campaign = await create(req)
    return campaign
```

**Rate Limit Headers:**

```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1682100060
```

**Response when rate limited:**

```
HTTP 429 Too Many Requests

{
    "error": "rate_limit_exceeded",
    "message": "Too many requests. Try again in 30 seconds",
    "retry_after": 30
}
```

---

### 4.3 CORS Policy

**CORS Configuration:**

```python
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Whitelist only
    allow_credentials=True,  # Allow cookies
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,  # Preflight cache (10 min)
)
```

**Rules:**

- ✅ Whitelist specific origins (never `*`)
- ✅ Allow credentials only if needed
- ✅ Specific HTTP methods only
- ✅ Specific headers only
- ✅ Preflight caching (reduces requests)

---

### 4.4 API Versioning

**Version Format:**

```
/api/v1/campaigns
/api/v2/campaigns

or

Accept: application/vnd.rpg-server.v1+json
```

**Breaking Changes:**

1. Add new version (v2)
2. Keep old version (v1) for 6 months
3. Deprecate old version (return warning header)
4. Sunset old version (return 410 Gone)

**Deprecation Process:**

```python
@app.get("/api/v1/campaigns")
async def list_campaigns_v1():
    # Add deprecation header
    response = Response()
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = (
        "Fri, 31 Dec 2026 23:59:59 GMT"  # End date
    )
    response.headers["Link"] = (
        '</api/v2/campaigns>; rel="successor-version"'
    )
    return response
```

---

## 📋 Part 5: Incident Response

### 5.1 Breach Notification Procedure

**On Security Incident:**

1. **Immediate (< 1 hour)**
   - Isolate affected system
   - Stop data leak (kill process, revoke tokens)
   - Preserve evidence (logs, memory dumps)
   - Notify security team

2. **Short-term (< 24 hours)**
   - Assess scope: What data exposed?
   - Assess impact: How many users?
   - Implement temporary fix
   - Start post-incident review

3. **Medium-term (< 72 hours)**
   - Notify affected users
   - Notify authorities (if required by law)
   - Provide credit monitoring (if PII exposed)
   - Communicate public disclosure

4. **Long-term (< 30 days)**
   - Root cause analysis
   - Implement permanent fix
   - Update security model
   - Training for team
   - Public post-mortem (blameless)

**Notification Template:**

```
Subject: Security Incident [TIMESTAMP]

Dear User,

We detected a security incident affecting [X] users.
This incident [did/did not] involve your personal data.

What happened:
- [Description of incident]

What we did:
- [Immediate actions taken]

What you should do:
- [Recommended actions for users]

For more information: [link to public statement]
```

---

### 5.2 Evidence Preservation

**Critical Evidence to Preserve:**

1. **Logs**
   - Authentication logs (failed attempts)
   - API access logs
   - Error logs
   - System logs

2. **Data**
   - Affected records (snapshot)
   - Transaction logs
   - Network traffic (if possible)

3. **Timing**
   - When incident discovered
   - When first anomaly occurred
   - When containment complete

**Preservation Rules:**

- ✅ Copy to immutable storage
- ✅ Timestamp everything
- ✅ Chain of custody
- ✅ Hash for integrity
- ✅ Encrypt for confidentiality

---

### 5.3 Post-Incident Review

**Blameless Post-Mortem:**

Conduct within 5 days, include:

1. **Timeline**
   - When was it detected?
   - When did it start?
   - When was it stopped?

2. **Root Cause**
   - What was the technical failure?
   - What was the human failure?
   - What was the process failure?

3. **Impact**
   - How many users affected?
   - How much data exposed?
   - Financial impact?

4. **Fixes (Immediate)**
   - What was done to stop it?
   - How do we prevent immediate recurrence?

5. **Fixes (Long-term)**
   - What changes prevent this class of bug?
   - What process changes needed?
   - What training needed?

6. **Prevention**
   - New monitoring alerts?
   - New validation rules?
   - New testing?

---

## 📋 Part 6: Compliance & Governance

### 6.1 Compliance Requirements

**By Jurisdiction:**

**European Union (GDPR):**
- ✅ Right to be forgotten (data deletion)
- ✅ Right to access (export user data)
- ✅ Right to object (opt-out)
- ✅ Data Protection Impact Assessment (DPIA)
- ✅ Data Protection Officer (if needed)
- ✅ Incident notification (72 hours)

**United States (CCPA):**
- ✅ Right to access data
- ✅ Right to delete data
- ✅ Right to opt-out of sale
- ✅ Non-discrimination for exercising rights
- ✅ Incident notification (varies by state)

**Payment Card Industry (PCI DSS):**
- ❌ Don't store credit card data
- ✅ If stored: Full PCI compliance
- ✅ Use payment processor instead

---

### 6.2 Security Audit Checklist

**Monthly:**
- [ ] Review access logs for anomalies
- [ ] Check for failed authentication patterns
- [ ] Verify encryption keys rotated
- [ ] Check dependency vulnerabilities

**Quarterly:**
- [ ] Full security review (this model)
- [ ] Threat model update
- [ ] Penetration test
- [ ] Code security audit

**Annually:**
- [ ] External security audit
- [ ] Compliance review (GDPR, etc.)
- [ ] Security training for team
- [ ] Incident drill/simulation

---

### 6.3 Security Metrics

**Monitor These:**

| Metric | Target | Alert |
|--------|--------|-------|
| Auth failures/min | < 5 | > 10 |
| Rate limit hits/hour | < 100 | > 500 |
| Failed validation/hour | 0 | > 1 |
| Token expirations | N/A | Log all |
| Unauthorized access attempts | 0 | Log all |

---

## 🔗 Related Documents

- [ADR-002: Async-First](../../decisions/ADR-002-async-first-no-blocking.md) — All security operations must be async
- [ADR-003: Ports & Adapters](../../decisions/ADR-003-ports-adapters-pattern.md) — Security at boundaries
- [Constitution](../core/rules/INDEX.md) — Security principles
- [Performance Model](./performance.md) — SLOs apply to security

---

## 📚 Implementation Roadmap

**Phase 1 (2 weeks):**
- [ ] Implement JWT authentication
- [ ] Implement RBAC authorization
- [ ] Add input validation (Pydantic)
- [ ] Setup rate limiting
- [ ] Add CORS configuration

**Phase 2 (2 weeks):**
- [ ] Implement encryption at rest (for secrets)
- [ ] Add HTTPS/TLS requirement
- [ ] Setup security headers
- [ ] Implement session timeout
- [ ] Create incident response procedures

**Phase 3 (2 weeks):**
- [ ] Add comprehensive audit logging
- [ ] Implement monitoring alerts
- [ ] Setup automated compliance checks
- [ ] Create security runbooks
- [ ] Team security training

---

## ✅ Validation

See section "Validation" in this ADR:
- [ ] Every HTTP endpoint authenticates
- [ ] Every endpoint authorizes (checks permissions)
- [ ] All inputs validated before use
- [ ] No sensitive data in logs
- [ ] All sensitive data encrypted
- [ ] HTTPS enforced in production
- [ ] Rate limiting working
- [ ] CORS whitelist configured
- [ ] Incident response procedure tested

**How to verify:**
```bash
# Run security compliance tests
pytest tests/contracts/security/ -v

# Check for hardcoded secrets
git log -p | grep -i "password\|api_key\|secret"

# Verify HTTPS enforcement
curl -i http://api.example.com  # Should 301 to https://

# Test rate limiting
for i in {1..51}; do curl /api/endpoint; done  # 51st should fail

# Audit access logs
tail -f /var/log/app/access.log | grep "401\|403"
```

---

## 📞 Security Contacts

**Report Security Issues:**
- Email: security@[PROJECT_DOMAIN]
- Do NOT create public GitHub issues
- Response time: < 24 hours
- Disclosure: 90 days (coordinated)

**Security Team:**
- Security Lead: [Contact]
- Incident Response: [Contact]
- On-Call: [Escalation procedure]

---

**Status:** ✅ Production-Ready
**Framework:** SPEC v1.0
**Owner:** Security Lead
**Review Cycle:** Quarterly (3 months)
**Next Review:** 2026-07-19
