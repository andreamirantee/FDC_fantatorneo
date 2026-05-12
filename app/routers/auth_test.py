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


@router.get("/auth", response_class=HTMLResponse)
def auth_login():
    """Pagina login.
    
    Returns:
        Pagina HTML con form login mobile-optimized.
    """
    return """
    <!doctype html>
    <html lang="it">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>FDCFANTA ✦ FDC Fantatorneo - Login</title>
        <style>
            :root {
                --theme-sky: #33ccff;
                --theme-pink: #ff80a8;
                --theme-yellow: #ffd24d;
                --theme-ink: #102033;
                --theme-bg: #1a2333;
                --theme-panel: rgba(31, 42, 61, 0.96);
                --theme-border: rgba(255, 255, 255, 0.12);
                --theme-text: #eef3fb;
                --theme-muted: rgba(238, 243, 251, 0.72);
            }
            * { box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: radial-gradient(circle at top left, rgba(51, 204, 255, 0.12), transparent 36%), radial-gradient(circle at top right, rgba(255, 128, 168, 0.10), transparent 32%), radial-gradient(circle at bottom center, rgba(255, 210, 77, 0.08), transparent 34%), var(--theme-bg); color: var(--theme-text); display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 16px; }
            .wrap { width: 100%; max-width: 560px; }
            .card { background: var(--theme-panel); border: 1px solid var(--theme-border); border-radius: 22px; padding: 34px; box-shadow: 0 24px 70px rgba(0,0,0,0.30); }
            input { width: 100%; box-sizing: border-box; margin: 0 0 16px; padding: 16px 18px; border-radius: 14px; border: 1px solid var(--theme-border); background: rgba(17,24,39,0.92); color: var(--theme-text); font-size: 16px; }
            input::placeholder { color: rgba(238, 243, 251, 0.52); }
            button { width: 100%; box-sizing: border-box; margin: 10px 0; padding: 16px 18px; border-radius: 999px; border: none; cursor: pointer; font-weight: 700; font-size: 16px; }
            button.primary { background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 100%); color: var(--theme-ink); }
            button.primary:hover { filter: brightness(1.05); }
            button.secondary { background: rgba(255,255,255,0.10); color: var(--theme-text); border: 1px solid rgba(255,255,255,0.08); }
            button.secondary:hover { background: rgba(255,255,255,0.14); }
            h2 { margin: 0 0 24px 0; font-size: 32px; line-height: 1.05; color: var(--theme-sky); }
            .auth-link { margin-top: 18px; font-size: 14px; color: var(--theme-muted); text-align: center; line-height: 1.6; }
            .auth-link a { color: var(--theme-yellow); text-decoration: none; font-weight: 700; cursor: pointer; }
            .auth-link a:hover { text-decoration: underline; }
            .warning-banner {
                display: none;
                background: linear-gradient(135deg, rgba(255, 128, 168, 0.18), rgba(255, 210, 77, 0.12));
                border: 1px solid rgba(255, 210, 77, 0.45);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                color: var(--theme-text);
            }
            .warning-banner h3 { margin: 0 0 6px 0; font-size: 15px; font-weight: 700; }
            .warning-banner p { margin: 4px 0; font-size: 13px; }
            .error-banner {
                display: none;
                background: linear-gradient(135deg, rgba(255, 107, 122, 0.20), rgba(255, 142, 181, 0.14));
                border: 1px solid rgba(255, 107, 122, 0.45);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                color: var(--theme-text);
            }
            .error-banner h3 { margin: 0 0 6px 0; font-size: 15px; font-weight: 700; }
            .error-banner p { margin: 4px 0; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="card">
                <h2><span style="display:inline-block; padding:6px 14px; border-radius:999px; background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 100%); color: var(--theme-ink); font-size: 13px; letter-spacing: 0.08em; margin-bottom: 12px;">FDCFANTA ✦</span><br>Accedi</h2>
                
                <div id="error-banner" class="error-banner">
                    <h3>Errore</h3>
                    <p id="error-text">Password errata o account non trovato.</p>
                </div>

                <div id="warning-banner" class="warning-banner">
                    <h3>Email non confermata</h3>
                    <p id="warning-text">Accedi alla tua email e conferma il link di verifica. Controlla anche Spam o Posta indesiderata.</p>
                    <button class="secondary" onclick="resendConfirmation()" style="margin-top: 8px;">Rinvia conferma email</button>
                </div>

                <input id="login-email" type="email" placeholder="Email" />
                <input id="login-password" type="password" placeholder="Password" />
                <button class="primary" onclick="loginUser()">Accedi</button>
                
                <p class="auth-link"><a onclick="goToForgot()">Hai dimenticato la password?</a></p>
                <p class="auth-link">Non hai un account? <a href="/register">Registrati</a></p>
            </div>
        </div>

        <script>
            function hideError() {
                document.getElementById("error-banner").style.display = "none";
            }
            
            function hideWarning() {
                document.getElementById("warning-banner").style.display = "none";
            }

            function showError(message) {
                document.getElementById("error-text").textContent = message;
                document.getElementById("error-banner").style.display = "block";
            }

            function showWarning() {
                document.getElementById("warning-banner").style.display = "block";
            }

            function goToForgot() {
                window.location.href = '/forgot';
            }

            async function loginUser() {
                try {
                    hideError();
                    hideWarning();
                    const email = document.getElementById("login-email").value;
                    const password = document.getElementById("login-password").value;
                    
                    if (!email || !password) {
                        showError("Inserisci email e password.");
                        return;
                    }

                    const response = await fetch("/api/v1/auth/login", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email, password }),
                    });
                    const payload = await response.json();
                    
                    if (payload.access_token) {
                        localStorage.setItem("fdc_access_token", payload.access_token);
                        setTimeout(() => {
                            window.location.href = '/home';
                        }, 600);
                        return;
                    }
                    
                    const detail = String(payload.detail || "").toLowerCase();
                    if (detail.includes("email not confirmed")) {
                        showWarning();
                        return;
                    }
                    if (detail.includes("invalid login credentials") || detail.includes("wrong password") || detail.includes("invalid credentials")) {
                        showError("Password errata o account non trovato.");
                        return;
                    }
                    
                    showError(payload.detail || "Errore durante l'accesso.");
                } catch (error) {
                    showError("Errore di connessione: " + String(error));
                }
            }

            async function resendConfirmation() {
                try {
                    const email = document.getElementById("login-email").value;
                    if (!email) {
                        showError("Inserisci la tua email.");
                        return;
                    }
                    const response = await fetch("/api/v1/auth/resend-confirmation", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email }),
                    });
                    const payload = await response.json();
                    if (response.ok) {
                        showError("Email di conferma inviata. Controlla la tua casella e anche Spam o Posta indesiderata.");
                    } else {
                        showError(payload.detail || "Errore nell'invio.");
                    }
                } catch (error) {
                    showError("Errore: " + String(error));
                }
            }
        </script>
    </body>
    </html>
    """


@router.get("/register", response_class=HTMLResponse)
def auth_register():
    """Pagina registrazione.
    
    Returns:
        Pagina HTML con form registrazione mobile-optimized.
    """
    return """
    <!doctype html>
    <html lang="it">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>FDCFANTA ✦ FDC Fantatorneo - Registrazione</title>
        <style>
            :root {
                --theme-sky: #33ccff;
                --theme-pink: #ff80a8;
                --theme-yellow: #ffd24d;
                --theme-ink: #102033;
                --theme-bg: #1a2333;
                --theme-panel: rgba(31, 42, 61, 0.96);
                --theme-border: rgba(255, 255, 255, 0.12);
                --theme-text: #eef3fb;
                --theme-muted: rgba(238, 243, 251, 0.72);
            }
            * { box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: radial-gradient(circle at top left, rgba(51, 204, 255, 0.12), transparent 36%), radial-gradient(circle at top right, rgba(255, 128, 168, 0.10), transparent 32%), radial-gradient(circle at bottom center, rgba(255, 210, 77, 0.08), transparent 34%), var(--theme-bg); color: var(--theme-text); display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 16px; }
            .wrap { width: 100%; max-width: 560px; }
            .card { background: var(--theme-panel); border: 1px solid var(--theme-border); border-radius: 22px; padding: 34px; box-shadow: 0 24px 70px rgba(0,0,0,0.30); }
            input { width: 100%; box-sizing: border-box; margin: 0 0 16px; padding: 16px 18px; border-radius: 14px; border: 1px solid var(--theme-border); background: rgba(17,24,39,0.92); color: var(--theme-text); font-size: 16px; }
            input::placeholder { color: rgba(238, 243, 251, 0.52); }
            button { width: 100%; box-sizing: border-box; margin: 10px 0; padding: 16px 18px; border-radius: 999px; border: none; cursor: pointer; font-weight: 700; font-size: 16px; }
            button.primary { background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 100%); color: var(--theme-ink); }
            button.primary:hover { filter: brightness(1.05); }
            button.secondary { background: rgba(255,255,255,0.10); color: var(--theme-text); border: 1px solid rgba(255,255,255,0.08); }
            button.secondary:hover { background: rgba(255,255,255,0.14); }
            h2 { margin: 0 0 24px 0; font-size: 32px; line-height: 1.05; color: var(--theme-sky); }
            .auth-link { margin-top: 18px; font-size: 14px; color: var(--theme-muted); text-align: center; line-height: 1.6; }
            .auth-link a { color: var(--theme-yellow); text-decoration: none; font-weight: 700; cursor: pointer; }
            .auth-link a:hover { text-decoration: underline; }
            .success-banner {
                display: none;
                background: linear-gradient(135deg, rgba(51, 204, 255, 0.16), rgba(255, 210, 77, 0.12));
                border: 1px solid rgba(51, 204, 255, 0.40);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                color: var(--theme-text);
            }
            .success-banner h3 { margin: 0 0 6px 0; font-size: 15px; font-weight: 700; }
            .success-banner p { margin: 4px 0; font-size: 13px; }
            .error-banner {
                display: none;
                background: linear-gradient(135deg, #7f1d1d, #b91c1c);
                border: 1px solid rgba(255, 107, 122, 0.45);
                border-radius: 12px;
                padding: 12px;
                margin-bottom: 16px;
                color: #fee2e2;
            }
            .error-banner h3 { margin: 0 0 6px 0; font-size: 15px; font-weight: 700; }
            .error-banner p { margin: 4px 0; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="card">
                <h2><span style="display:inline-block; padding:6px 14px; border-radius:999px; background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 100%); color: var(--theme-ink); font-size: 13px; letter-spacing: 0.08em; margin-bottom: 12px;">FDCFANTA ✦</span><br>Registrati</h2>
                
                <div id="success-banner" class="success-banner">
                    <h3>Registrazione completata</h3>
                    <p>Ti abbiamo inviato una email di conferma. Aprila e clicca il link per attivare l'account. Controlla anche Spam o Posta indesiderata.</p>
                </div>

                <div id="error-banner" class="error-banner">
                    <h3>Errore</h3>
                    <p id="error-text">Controlla i dati e riprova.</p>
                </div>

                <input id="reg-name" type="text" placeholder="Nome" />
                <input id="reg-surname" type="text" placeholder="Cognome" />
                <input id="reg-email" type="email" placeholder="Email" />
                <input id="reg-password" type="password" placeholder="Password" />
                <button class="primary" onclick="registerUser()">Crea account</button>
                
                <p class="auth-link">Hai già un account? <a href="/auth">Accedi</a></p>
            </div>
        </div>

        <script>
            function hideError() {
                document.getElementById("error-banner").style.display = "none";
            }

            function hideSuccess() {
                document.getElementById("success-banner").style.display = "none";
            }

            function showError(message) {
                document.getElementById("error-text").textContent = message;
                document.getElementById("error-banner").style.display = "block";
            }

            function showSuccess() {
                document.getElementById("success-banner").style.display = "block";
            }

            async function registerUser() {
                try {
                    hideError();
                    hideSuccess();
                    const name = document.getElementById("reg-name").value;
                    const surname = document.getElementById("reg-surname").value;
                    const email = document.getElementById("reg-email").value;
                    const password = document.getElementById("reg-password").value;
                    
                    if (!name || !surname || !email || !password) {
                        showError("Compila tutti i campi.");
                        return;
                    }

                    const response = await fetch("/api/v1/auth/register", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ name, surname, email, password }),
                    });
                    const payload = await response.json();
                    
                    if (response.ok) {
                        showSuccess();
                        setTimeout(() => {
                            window.location.href = '/auth';
                        }, 3000);
                        return;
                    }
                    
                    showError(payload.detail || "Errore durante la registrazione.");
                } catch (error) {
                    showError("Errore di connessione: " + String(error));
                }
            }
        </script>
    </body>
    </html>
    """


@router.get("/forgot", response_class=HTMLResponse)
def auth_forgot():
    """Pagina reset password.
    
    Returns:
        Pagina HTML con form per richiedere reset password.
    """
    return """
    <!doctype html>
    <html lang="it">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>FDCFANTA ✦ FDC Fantatorneo - Reset Password</title>
        <style>
            :root {
                --theme-sky: #33ccff;
                --theme-pink: #ff80a8;
                --theme-yellow: #ffd24d;
                --theme-ink: #102033;
                --theme-bg: #1a2333;
                --theme-panel: rgba(31, 42, 61, 0.96);
                --theme-border: rgba(255, 255, 255, 0.12);
                --theme-text: #eef3fb;
                --theme-muted: rgba(238, 243, 251, 0.72);
            }
            * { box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: radial-gradient(circle at top left, rgba(51, 204, 255, 0.12), transparent 36%), radial-gradient(circle at top right, rgba(255, 128, 168, 0.10), transparent 32%), radial-gradient(circle at bottom center, rgba(255, 210, 77, 0.08), transparent 34%), var(--theme-bg); color: var(--theme-text); display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 16px; }
            .wrap { width: 100%; max-width: 380px; }
            .card { background: var(--theme-panel); border: 1px solid var(--theme-border); border-radius: 18px; padding: 24px; box-shadow: 0 20px 60px rgba(0,0,0,0.28); }
            input { width: 100%; box-sizing: border-box; margin: 0 0 12px; padding: 12px; border-radius: 10px; border: 1px solid var(--theme-border); background: rgba(17,24,39,0.92); color: var(--theme-text); font-size: 14px; }
            input::placeholder { color: rgba(238, 243, 251, 0.52); }
            button { width: 100%; box-sizing: border-box; margin: 8px 0; padding: 12px; border-radius: 999px; border: none; cursor: pointer; font-weight: 700; font-size: 14px; }
            button.primary { background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 100%); color: var(--theme-ink); }
            button.primary:hover { filter: brightness(1.05); }
            button.secondary { background: rgba(255,255,255,0.10); color: var(--theme-text); border: 1px solid rgba(255,255,255,0.08); }
            button.secondary:hover { background: rgba(255,255,255,0.14); }
            h2 { margin: 0 0 24px 0; font-size: 32px; line-height: 1.05; color: var(--theme-sky); }
            .subtitle { margin: 0 0 18px 0; font-size: 15px; color: var(--theme-muted); line-height: 1.6; }
            .auth-link { margin-top: 18px; font-size: 14px; color: var(--theme-muted); text-align: center; line-height: 1.6; }
            .auth-link a { color: var(--theme-yellow); text-decoration: none; font-weight: 700; cursor: pointer; }
            .auth-link a:hover { text-decoration: underline; }
            .success-banner {
                display: none;
                background: linear-gradient(135deg, rgba(51, 204, 255, 0.16), rgba(255, 210, 77, 0.12));
                border: 1px solid rgba(51, 204, 255, 0.40);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                color: var(--theme-text);
            }
            .success-banner h3 { margin: 0 0 6px 0; font-size: 15px; font-weight: 700; }
            .success-banner p { margin: 4px 0; font-size: 13px; }
            .error-banner {
                display: none;
                background: linear-gradient(135deg, rgba(255, 107, 122, 0.20), rgba(255, 142, 181, 0.14));
                border: 1px solid rgba(255, 107, 122, 0.45);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                color: var(--theme-text);
            }
            .error-banner h3 { margin: 0 0 6px 0; font-size: 15px; font-weight: 700; }
            .error-banner p { margin: 4px 0; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="card">
                <h2><span style="display:inline-block; padding:6px 14px; border-radius:999px; background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 100%); color: var(--theme-ink); font-size: 13px; letter-spacing: 0.08em; margin-bottom: 12px;">FDCFANTA ✦</span><br>Recupera Password</h2>
                <p class="subtitle">Inserisci la tua email per ricevere un link di reset della password.</p>
                
                <div id="success-banner" class="success-banner">
                    <h3>Email inviata</h3>
                    <p>Controlla la tua casella di posta e segui il link per resettare la password.</p>
                </div>

                <div id="error-banner" class="error-banner">
                    <h3>Errore</h3>
                    <p id="error-text">Controlla l'email e riprova.</p>
                </div>

                <input id="forgot-email" type="email" placeholder="Email" />
                <button class="primary" onclick="requestReset()">Invia Reset Link</button>
                
                <p class="auth-link">Ricordi la password? <a href="/auth">Accedi</a></p>
                <p class="auth-link">Non hai un account? <a href="/register">Registrati</a></p>
            </div>
        </div>

        <script>
            function hideError() {
                document.getElementById("error-banner").style.display = "none";
            }

            function hideSuccess() {
                document.getElementById("success-banner").style.display = "none";
            }

            function showError(message) {
                document.getElementById("error-text").textContent = message;
                document.getElementById("error-banner").style.display = "block";
            }

            function showSuccess() {
                document.getElementById("success-banner").style.display = "block";
            }

            async function requestReset() {
                try {
                    hideError();
                    hideSuccess();
                    const email = document.getElementById("forgot-email").value;
                    
                    if (!email) {
                        showError("Inserisci la tua email.");
                        return;
                    }

                    // Nota: Assicurati che il backend abbia un endpoint POST /api/v1/auth/request-password-reset
                    const response = await fetch("/api/v1/auth/request-password-reset", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email }),
                    });
                    const payload = await response.json();
                    
                    if (response.ok) {
                        showSuccess();
                        setTimeout(() => {
                            window.location.href = '/auth';
                        }, 4000);
                        return;
                    }
                    
                    showError(payload.detail || "Errore nell'invio del reset link.");
                } catch (error) {
                    showError("Errore di connessione: " + String(error));
                }
            }
        </script>
    </body>
    </html>
    """


@router.get("/reset-password", response_class=HTMLResponse)
def auth_reset_password():
    """Pagina completamento reset password con token dalla URL.
    
    Returns:
        Pagina HTML con form per inserire nuova password.
    """
    return """
    <!doctype html>
    <html lang="it">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>FDCFANTA ✦ FDC Fantatorneo - Reset Password</title>
        <style>
            :root {
                --theme-sky: #33ccff;
                --theme-pink: #ff80a8;
                --theme-yellow: #ffd24d;
                --theme-ink: #102033;
                --theme-bg: #1a2333;
                --theme-panel: rgba(31, 42, 61, 0.96);
                --theme-border: rgba(255, 255, 255, 0.12);
                --theme-text: #eef3fb;
                --theme-muted: rgba(238, 243, 251, 0.72);
            }
            * { box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: radial-gradient(circle at top left, rgba(51, 204, 255, 0.12), transparent 36%), radial-gradient(circle at top right, rgba(255, 128, 168, 0.10), transparent 32%), radial-gradient(circle at bottom center, rgba(255, 210, 77, 0.08), transparent 34%), var(--theme-bg); color: var(--theme-text); display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 16px; }
            .wrap { width: 100%; max-width: 560px; }
            .card { background: var(--theme-panel); border: 1px solid var(--theme-border); border-radius: 22px; padding: 34px; box-shadow: 0 24px 70px rgba(0,0,0,0.30); }
            input { width: 100%; box-sizing: border-box; margin: 0 0 16px; padding: 16px 18px; border-radius: 14px; border: 1px solid var(--theme-border); background: rgba(17,24,39,0.92); color: var(--theme-text); font-size: 16px; }
            input::placeholder { color: rgba(238, 243, 251, 0.52); }
            button { width: 100%; box-sizing: border-box; margin: 10px 0; padding: 16px 18px; border-radius: 999px; border: none; cursor: pointer; font-weight: 700; font-size: 16px; }
            button.primary { background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 100%); color: var(--theme-ink); }
            button.primary:hover { filter: brightness(1.05); }
            button.secondary { background: rgba(255,255,255,0.10); color: var(--theme-text); border: 1px solid rgba(255,255,255,0.08); }
            button.secondary:hover { background: rgba(255,255,255,0.14); }
            h2 { margin: 0 0 24px 0; font-size: 32px; line-height: 1.05; color: var(--theme-sky); }
            .subtitle { margin: 0 0 18px 0; font-size: 15px; color: var(--theme-muted); line-height: 1.6; }
            .auth-link { margin-top: 18px; font-size: 14px; color: var(--theme-muted); text-align: center; line-height: 1.6; }
            .auth-link a { color: var(--theme-yellow); text-decoration: none; font-weight: 700; cursor: pointer; }
            .auth-link a:hover { text-decoration: underline; }
            .success-banner {
                display: none;
                background: linear-gradient(135deg, rgba(51, 204, 255, 0.16), rgba(255, 210, 77, 0.12));
                border: 1px solid rgba(51, 204, 255, 0.40);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                color: var(--theme-text);
            }
            .success-banner h3 { margin: 0 0 6px 0; font-size: 15px; font-weight: 700; }
            .success-banner p { margin: 4px 0; font-size: 13px; }
            .error-banner {
                display: none;
                background: linear-gradient(135deg, rgba(255, 107, 122, 0.20), rgba(255, 142, 181, 0.14));
                border: 1px solid rgba(255, 107, 122, 0.45);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                color: var(--theme-text);
            }
            .error-banner h3 { margin: 0 0 6px 0; font-size: 15px; font-weight: 700; }
            .error-banner p { margin: 4px 0; font-size: 13px; }
            .info-banner {
                display: none;
                background: linear-gradient(135deg, rgba(51, 204, 255, 0.16), rgba(255, 128, 168, 0.12));
                border: 1px solid rgba(51, 204, 255, 0.40);
                border-radius: 12px;
                padding: 12px;
                margin-bottom: 16px;
                color: var(--theme-text);
            }
            .info-banner h3 { margin: 0 0 6px 0; font-size: 14px; font-weight: 700; }
            .info-banner p { margin: 4px 0; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="card">
                <h2><span style="display:inline-block; padding:6px 14px; border-radius:999px; background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 100%); color: var(--theme-ink); font-size: 13px; letter-spacing: 0.08em; margin-bottom: 12px;">FDCFANTA ✦</span><br>Imposta Nuova Password</h2>
                <p class="subtitle">Inserisci la tua nuova password per completare il reset.</p>
                
                <div id="info-banner" class="info-banner">
                    <h3>Caricamento...</h3>
                    <p id="info-text">Verificazione token in corso...</p>
                </div>

                <div id="success-banner" class="success-banner">
                    <h3>Password resettata</h3>
                    <p>Accedi con la tua nuova password.</p>
                </div>

                <div id="error-banner" class="error-banner">
                    <h3>Errore</h3>
                    <p id="error-text">Il link di reset è scaduto o non valido.</p>
                </div>

                <input id="new-password" type="password" placeholder="Nuova password" />
                <input id="confirm-password" type="password" placeholder="Conferma password" />
                <button class="primary" onclick="completeReset()">Salva Password</button>
                
                <p class="auth-link"><a href="/auth">Torna al login</a></p>
            </div>
        </div>

        <script>
            let resetToken = null;

            function hideInfo() {
                document.getElementById("info-banner").style.display = "none";
            }

            function hideError() {
                document.getElementById("error-banner").style.display = "none";
            }

            function hideSuccess() {
                document.getElementById("success-banner").style.display = "none";
            }

            function showError(message) {
                document.getElementById("error-text").textContent = message;
                document.getElementById("error-banner").style.display = "block";
                hideInfo();
            }

            function showSuccess() {
                document.getElementById("success-banner").style.display = "block";
                hideInfo();
            }

            function showInfo(message) {
                document.getElementById("info-text").textContent = message;
                document.getElementById("info-banner").style.display = "block";
            }

            // Estrai token dalla URL (#access_token=...)
            function extractToken() {
                const hash = window.location.hash.substring(1);
                const params = new URLSearchParams(hash);
                return params.get("access_token");
            }

            function initPage() {
                resetToken = extractToken();
                hideInfo();
                
                if (!resetToken) {
                    showError("Link di reset non valido. Richiedi un nuovo reset.");
                    return;
                }
                showInfo("Token verificato. Inserisci la nuova password.");
            }

            async function completeReset() {
                try {
                    hideError();
                    hideSuccess();
                    
                    if (!resetToken) {
                        showError("Link di reset non valido. Richiedi un nuovo reset.");
                        return;
                    }
                    
                    const newPassword = document.getElementById("new-password").value;
                    const confirmPassword = document.getElementById("confirm-password").value;
                    
                    if (!newPassword || !confirmPassword) {
                        showError("Inserisci e conferma la nuova password.");
                        return;
                    }
                    
                    if (newPassword !== confirmPassword) {
                        showError("Le password non coincidono.");
                        return;
                    }
                    
                    if (newPassword.length < 6) {
                        showError("La password deve avere almeno 6 caratteri.");
                        return;
                    }

                    const response = await fetch("/api/v1/auth/reset-password", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ token: resetToken, password: newPassword }),
                    });
                    const payload = await response.json();
                    
                    if (response.ok) {
                        showSuccess();
                        setTimeout(() => {
                            window.location.href = '/auth';
                        }, 3000);
                        return;
                    }
                    
                    showError(payload.detail || "Errore nel reset della password.");
                } catch (error) {
                    showError("Errore di connessione: " + String(error));
                }
            }

            // Inizializza pagina
            initPage();
        </script>
    </body>
    </html>
    """