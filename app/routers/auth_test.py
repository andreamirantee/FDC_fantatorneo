"""Playground autenticazione basato su browser.

Fornisce UI HTML interattiva per test manuale dei flussi auth:
- Registrazione utente con conferma email
- Login con recupero token JWT
- Salvataggio token e richieste autenticate
- Funzionalità reinvio email di conferma

Nota: Solo per sviluppo/testing. Non per produzione.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

# Router playground: interfaccia HTML testing interattiva (senza prefix API).
router = APIRouter(tags=["Auth Test"])


@router.get("/playground/auth", response_class=HTMLResponse)
def auth_playground():
    """Fornisci pagina HTML testing auth interattiva.
    
    Fornisce form per:
    - Registrazione (name, email, password) → email conferma inviata
    - Login (email, password) → ritorna token JWT access (salvato in localStorage)
    - Lettura profilo (/users/me) con bearer token
    - Reinvio conferma (per retry verificazione email)
    
    Returns:
        Pagina HTML con form stilizzati e handler JavaScript.
    """
    return """
    <!doctype html>
    <html lang="it">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>FDC Fantatorneo - Auth Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
            .wrap { max-width: 920px; margin: 0 auto; padding: 24px; }
            .card { background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 20px; margin-bottom: 18px; }
            input, button, textarea { width: 100%; box-sizing: border-box; margin: 6px 0 12px; padding: 12px; border-radius: 10px; border: 1px solid #334155; background: #0b1220; color: #e2e8f0; }
            button { background: #2563eb; border: none; cursor: pointer; font-weight: 700; }
            button.secondary { background: #475569; }
            pre { white-space: pre-wrap; word-break: break-word; background: #020617; padding: 14px; border-radius: 12px; min-height: 120px; }
            h1, h2 { margin-top: 0; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
            @media (max-width: 760px) { .grid { grid-template-columns: 1fr; } }
            .row { display: flex; gap: 10px; flex-wrap: wrap; }
            .row button { flex: 1 1 200px; }
            .auth-link {
                margin-top: 10px;
                font-size: 14px;
                color: #cbd5e1;
            }
            .auth-link a {
                color: #60a5fa;
                text-decoration: none;
                font-weight: 700;
                cursor: pointer;
            }
            .auth-link a:hover { text-decoration: underline; }
            .register-panel { display: none; }
            .success-banner {
                display: none;
                background: linear-gradient(135deg, #0f766e, #0b5c49);
                border: 1px solid #34d399;
                border-radius: 16px;
                padding: 18px;
                margin-bottom: 18px;
                color: #ecfeff;
            }
            .success-banner h2 { margin-bottom: 8px; }
            .warning-banner {
                display: none;
                background: linear-gradient(135deg, #7c2d12, #9a3412);
                border: 1px solid #fb923c;
                border-radius: 16px;
                padding: 18px;
                margin-bottom: 18px;
                color: #fff7ed;
            }
            .warning-banner h2 { margin-bottom: 8px; }
        </style>
    </head>
    <body>
        <div class="wrap">
            <h1>FDC Fantatorneo - Auth Test</h1>
            <p>Usa questa pagina per provare registrazione, login e lettura del profilo Supabase.</p>

            <div id="register-success" class="success-banner">
                <h2>Registrazione completata</h2>
                <p>Abbiamo inviato una mail di conferma all'indirizzo inserito. Aprila e conferma l'account per continuare.</p>
                <p id="register-success-email" style="margin-bottom: 0; font-weight: 700;"></p>
            </div>

            <div id="email-not-confirmed" class="warning-banner">
                <h2>Email non confermata</h2>
                <p>Prima di fare login devi confermare l'email. Se non trovi il messaggio, usa il pulsante "Reinvia mail di conferma".</p>
                <p id="email-not-confirmed-address" style="margin-bottom: 0; font-weight: 700;"></p>
                <button class="secondary" onclick="resendFromWarning()">Reinvia adesso</button>
            </div>

            <div class="grid">
                <div class="card">
                    <h2>Login</h2>
                    <input id="login-email" placeholder="Email" type="email" />
                    <input id="login-password" placeholder="Password" type="password" />
                    <button onclick="loginUser()">Entra</button>
                    <button class="secondary" onclick="resendConfirmation()">Reinvia mail di conferma</button>
                    <button class="secondary" onclick="loadMe()">Leggi /users/me</button>
                    <button class="secondary" onclick="goToAdmin()">Accedi ad admin</button>
                    <p class="auth-link">Non hai un account? <a onclick="toggleRegisterSection()">Registrati</a></p>
                </div>
            </div>

            <div id="register-section" class="card register-panel">
                <h2>Registrazione</h2>
                <input id="reg-name" placeholder="Nome" />
                <input id="reg-surname" placeholder="Cognome" />
                <input id="reg-email" placeholder="Email" type="email" />
                <input id="reg-password" placeholder="Password" type="password" />
                <button onclick="registerUser()">Crea account</button>
            </div>

            <div class="card">
                <h2>Risposta</h2>
                <p style="margin-top:-6px; color:#94a3b8;">Nota: per registrarti usa una email vera, altrimenti Supabase puo rifiutarla.</p>
                <p style="margin-top:-8px; color:#94a3b8;">Se riprovi molte volte, Supabase puo anche applicare un rate limit temporaneo.</p>
                <pre id="output">Pronto.</pre>
            </div>
        </div>

        <script>
            function setOutput(value) {
                document.getElementById("output").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
            }

            function showRegisterSuccess(email) {
                document.getElementById("register-success-email").textContent = `Email inviata a: ${email}`;
                document.getElementById("register-success").style.display = "block";
            }

            function hideRegisterSuccess() {
                document.getElementById("register-success").style.display = "none";
                document.getElementById("register-success-email").textContent = "";
            }

            function showEmailNotConfirmed(email) {
                document.getElementById("login-email").value = email;
                document.getElementById("email-not-confirmed-address").textContent = `Account: ${email}`;
                document.getElementById("email-not-confirmed").style.display = "block";
            }

            function hideEmailNotConfirmed() {
                document.getElementById("email-not-confirmed").style.display = "none";
                document.getElementById("email-not-confirmed-address").textContent = "";
            }

            function toggleRegisterSection() {
                const section = document.getElementById("register-section");
                const isVisible = section.style.display === "block";
                section.style.display = isVisible ? "none" : "block";
                if (!isVisible) {
                    section.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            }

            function goToAdmin() {
                window.location.href = "/admin";
            }

            async function registerUser() {
                try {
                    hideRegisterSuccess();
                    hideEmailNotConfirmed();
                    const email = document.getElementById("reg-email").value;
                    const response = await fetch("/api/v1/auth/register", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            name: document.getElementById("reg-name").value,
                            surname: document.getElementById("reg-surname").value,
                            email: email,
                            password: document.getElementById("reg-password").value,
                        }),
                    });
                    const payload = await response.json();
                    setOutput(payload);
                    if (response.ok) {
                        showRegisterSuccess(email);
                    }
                } catch (error) {
                    setOutput({ error: String(error) });
                }
            }

            async function loginUser() {
                try {
                    hideEmailNotConfirmed();
                    const email = document.getElementById("login-email").value;
                    const response = await fetch("/api/v1/auth/login", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            email: email,
                            password: document.getElementById("login-password").value,
                        }),
                    });
                    const payload = await response.json();
                    if (payload.access_token) {
                        localStorage.setItem("fdc_access_token", payload.access_token);
                        // Redirect alla dashboard dopo login riuscito
                        setTimeout(() => {
                            window.location.href = '/market-test';
                        }, 800);
                    }
                    const detail = String(payload.detail || "").toLowerCase();
                    if (!response.ok && detail.includes("email not confirmed")) {
                        showEmailNotConfirmed(email);
                    }
                    if (!response.ok && (detail.includes("invalid login credentials") || detail.includes("wrong password") || detail.includes("invalid credentials"))) {
                        setOutput({
                            error: "Le credenziali Auth non coincidono. Se hai eliminato solo l'utente locale, l'account Supabase esiste ancora con la password vecchia. Fai reset password o usa la password precedente.",
                            detail: payload.detail,
                        });
                        return;
                    }
                    setOutput(payload);
                } catch (error) {
                    setOutput({ error: String(error) });
                }
            }

            async function resendConfirmation() {
                try {
                    const email = document.getElementById("login-email").value;
                    const response = await fetch("/api/v1/auth/resend-confirmation", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email }),
                    });
                    setOutput(await response.json());
                } catch (error) {
                    setOutput({ error: String(error) });
                }
            }

            async function resendFromWarning() {
                await resendConfirmation();
            }

            async function loadMe() {
                try {
                    const token = localStorage.getItem("fdc_access_token");
                    const response = await fetch("/api/v1/users/me", {
                        headers: token ? { "Authorization": `Bearer ${token}` } : {},
                    });
                    setOutput(await response.json());
                } catch (error) {
                    setOutput({ error: String(error) });
                }
            }
        </script>
    </body>
    </html>
    """