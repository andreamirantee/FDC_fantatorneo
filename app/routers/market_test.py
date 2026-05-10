"""Playground mercato con classifica e filtri partecipanti.

Interfaccia HTML interattiva per testare transazioni:
- Accessibile SOLO dopo login riuscito su auth-test
- Visualizzazione classifica (ranking) con 3 sport
- Filtri per partecipanti (ruolo, costo, team)
- Bottoni per buy/sell operazioni mercato
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from ..auth import get_current_user

router = APIRouter(tags=["Market Test"], include_in_schema=False)


@router.get("/market-test")
def serve_market_test():
    """Pagina HTML interattiva per testare mercato e transazioni.
    
    Pubblica: il controllo autenticazione è fatto via JavaScript con token localStorage.
    """
    
    # Dati placeholder per l'utente (sarà visualizzato dal JS con token dal localStorage)
    user_email = "Caricamento..."
    
    html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mercato Fantasy - Test</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header-left h1 {{ font-size: 2.5em; margin-bottom: 5px; }}
        .header-left p {{ opacity: 0.9; }}
        .header-right {{
            text-align: right;
            background: rgba(255,255,255,0.1);
            padding: 15px 20px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 15px;
        }}
        .dome-balance {{
            background: rgba(255,255,255,0.12);
            padding: 8px 12px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 14px;
            color: #fff;
            min-width: 140px;
            text-align: right;
        }}
        .user-greeting {{
            font-size: 13px;
            opacity: 0.9;
            white-space: nowrap;
        }}
        .btn-logout {{
            background: #ef4444;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
        }}
        .btn-logout:hover {{ background: #dc2626; }}
        .protected-badge {{
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }}
        
        .content {{
            display: flex;
            min-height: 600px;
        }}
        
        .tabs {{
            width: 250px;
            background: #f5f5f5;
            border-right: 1px solid #ddd;
            padding: 20px 0;
        }}
        .tab-btn {{
            width: 100%;
            padding: 15px 20px;
            border: none;
            background: none;
            cursor: pointer;
            text-align: left;
            font-size: 14px;
            color: #333;
            border-left: 4px solid transparent;
            transition: all 0.3s;
        }}
        .tab-btn:hover {{ background: #e0e0e0; }}
        .tab-btn.active {{
            background: white;
            border-left-color: #667eea;
            color: #667eea;
            font-weight: 600;
        }}
        
        .panel {{
            flex: 1;
            padding: 40px;
            display: none;
            overflow-y: auto;
        }}
        .panel.active {{ display: block; }}
        
        .ranking-container {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }}
        .ranking-table {{
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }}
        .ranking-table h3 {{
            background: #667eea;
            color: white;
            padding: 15px;
            margin: 0;
        }}
        .ranking-table table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .ranking-table th {{
            background: #f0f0f0;
            padding: 10px;
            text-align: left;
            font-size: 12px;
            font-weight: 600;
            color: #333;
        }}
        .ranking-table td {{
            padding: 10px;
            border-top: 1px solid #eee;
        }}
        .ranking-table tr:hover {{ background: #f5f5f5; }}
        
        .volley-container {{
            display: flex;
            flex-direction: column;
        }}
        .volley-tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #ddd;
        }}
        .volley-tab-btn {{
            padding: 12px 24px;
            border: none;
            background: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }}
        .volley-tab-btn:hover {{
            color: #333;
            background: #f5f5f5;
        }}
        .volley-tab-btn.active {{
            color: #667eea;
            border-bottom-color: #667eea;
        }}
        .volley-tab-content {{
            display: none;
        }}
        .volley-tab-content.active {{
            display: block;
        }}

        .score-card {{
            background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
            color: white;
            border-radius: 16px;
            padding: 28px;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
        }}
        .score-card h3 {{
            font-size: 28px;
            margin-bottom: 8px;
        }}
        .score-card p {{
            opacity: 0.92;
            line-height: 1.5;
        }}
        .score-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-top: 22px;
        }}
        .score-metric {{
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 14px;
            padding: 16px;
        }}
        .score-metric .label {{
            display: block;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            opacity: 0.75;
            margin-bottom: 8px;
        }}
        .score-metric .value {{
            font-size: 24px;
            font-weight: 700;
        }}
        .my-score-list {{
            margin-top: 20px;
            background: rgba(255,255,255,0.08);
            border-radius: 12px;
            overflow: hidden;
        }}
        .my-score-list table {{
            width: 100%;
            border-collapse: collapse;
            color: white;
        }}
        .my-score-list th,
        .my-score-list td {{
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255,255,255,0.12);
            text-align: left;
            font-size: 13px;
        }}
        .my-score-list th {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            opacity: 0.8;
        }}
        
        .filters {{
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }}
        .filter-group label {{
            display: block;
            font-size: 12px;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .filter-group input,
        .filter-group select {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 13px;
        }}
        
        .participants-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }}
        .participants-table th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        .participants-table td {{
            padding: 12px 15px;
            border-top: 1px solid #eee;
        }}
        .participants-table tr:hover {{ background: #f5f5f5; }}
        
        .btn {{
            padding: 10px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .btn-buy {{
            background: #10b981;
            color: white;
        }}
        .btn-buy:hover {{ background: #059669; }}
        .btn-sell {{
            background: #ef4444;
            color: white;
        }}
        .btn-sell:hover {{ background: #dc2626; }}
        .btn-go-market {{
            background: #667eea;
            color: white;
            padding: 12px 30px;
            margin-top: 20px;
            font-size: 14px;
        }}
        .btn-go-market:hover {{ background: #5568d3; }}
        .btn-buy-section {{
            background: #10b981;
            color: white;
            padding: 12px 30px;
            margin-top: 20px;
            font-size: 14px;
        }}
        .btn-buy-section:hover {{ background: #059669; }}
        
        .status {{
            margin-top: 20px;
            padding: 15px;
            border-radius: 4px;
            display: none;
        }}
        .status.success {{ background: #d1fae5; color: #065f46; border: 1px solid #6ee7b7; display: block; }}
        .status.error {{ background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; display: block; }}
        .status.info {{ background: #dbeafe; color: #0c2d6b; border: 1px solid #93c5fd; display: block; }}
        
        .loading {{ opacity: 0.6; pointer-events: none; }}
        
        
        .ranking-table tbody tr {{
            cursor: pointer;
        }}
        .ranking-table tbody tr:active {{
            background: #e0e0ff !important;
        }}
        
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
        }}
        .modal-content {{
            background: white;
            margin: 5% auto;
            padding: 30px;
            border-radius: 12px;
            width: 90%;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 15px;
        }}
        .modal-header h2 {{
            margin: 0;
            color: #333;
        }}
        .modal-close {{
            font-size: 28px;
            font-weight: bold;
            color: #aaa;
            cursor: pointer;
            line-height: 20px;
        }}
        .modal-close:hover {{
            color: #000;
        }}
        .modal-stats {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}
        .modal-stat-box {{
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .modal-stat-label {{
            font-size: 12px;
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .modal-stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: #667eea;
        }}
        .modal-info {{
            background: #f0f4ff;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
            font-size: 13px;
            color: #333;
        }}
    </style>
</head>
<body>
    <div id="detailModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">Dettagli Squadra</h2>
                <span class="modal-close" onclick="closeDetailModal()">&times;</span>
            </div>
            <div id="modalBody"></div>
        </div>
    </div>
    
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1>⚽ Mercato Fantasy - Test <span class="protected-badge">🔐 Protetto</span></h1>
                <p>Sessione autenticata - classifica e filtri partecipanti</p>
            </div>
            <div class="header-right">
                <div class="user-greeting">👤 <span id="userGreeting">Caricamento...</span></div>
                <div id="domeBalance" class="dome-balance">DomeCoin: —</div>
                <button class="btn-logout" onclick="logout()">Esci</button>
            </div>
        </div>
        
        <div class="content">
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('ranking')">📊 Classifica</button>
                <button class="tab-btn" onclick="switchTab('myScore')">⭐ Il mio punteggio</button>
                <button class="tab-btn" onclick="switchTab('market')">🛒 Mercato Partecipanti</button>
            </div>
            
            <div class="panel active" id="ranking">
                <h2>Classifiche degli sport</h2>
                <p style="color: #666; margin: 10px 0 30px; font-size: 14px;">
                    Visualizzazione delle classifiche divise per sport principali
                </p>
                <div class="ranking-container" id="rankingContainer">
                    <div style="text-align: center; grid-column: 1/-1; padding: 40px; color: #999;">
                        Caricamento classifica...
                    </div>
                </div>
                <div id="fetchStatus" style="padding:10px 20px; color:#b91c1c; font-weight:700;"></div>
                <button class="btn-go-market" onclick="switchTab('myScore')">→ Vai al mio punteggio</button>
            </div>

            <div class="panel" id="myScore">
                <h2>Il mio punteggio</h2>
                <p style="color: #666; margin: 10px 0 20px; font-size: 14px;">
                    Qui vedi solo il tuo punteggio, separato per ogni participant del tuo team.
                </p>

                <div class="score-card" id="myScoreContainer">
                    <h3>Caricamento punteggio...</h3>
                    <p>Sto recuperando il tuo team e il relativo punteggio.</p>
                </div>

                <button class="btn-go-market" onclick="switchTab('ranking')">→ Torna alle classifiche</button>
            </div>

            <div class="panel" id="market">
                <h2>Partecipanti Disponibili</h2>
                <p style="color: #666; margin: 10px 0 20px; font-size: 14px;">
                    Cerca e filtra partecipanti: se una squadra e tua vedi "Vendi", altrimenti "Acquista"
                </p>
                
                <div class="filters">
                    <div class="filter-group">
                        <label>Ricerca Nome</label>
                        <input type="text" id="filterName" onchange="applyFilters()">
                    </div>
                    <div class="filter-group">
                        <label>Ruolo</label>
                        <select id="filterRole" onchange="applyFilters()">
                            <option value="">Tutti</option>
                            <option value="Calcio">Calcio</option>
                            <option value="Pallavolo">Pallavolo</option>
                            <option value="Padel">Padel</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>Costo Max</label>
                        <input type="number" id="filterCost" value="100" onchange="applyFilters()">
                    </div>
                    <div class="filter-group">
                        <label>Squadra</label>
                        <input type="text" id="filterTeam" onchange="applyFilters()">
                    </div>
                </div>
                
                <table class="participants-table">
                    <thead>
                        <tr>
                            <th>Pos</th>
                            <th>Squadra</th>
                            <th>Ruolo</th>
                            <th>Punti</th>
                            <th>Costo</th>
                            <th>Stato</th>
                            <th>Azione</th>
                        </tr>
                    </thead>
                    <tbody id="participantsTable">
                        <tr><td colspan="7" style="text-align: center; padding: 20px; color: #999;">Caricamento partecipanti...</td></tr>
                    </tbody>
                </table>
                <div class="status" id="status"></div>
            </div>

        </div>
    </div>
    
    <script>
        // Usa path relativo per evitare problemi di host/porta quando l'app è proxata
        const API_BASE = '/api/v1';
        let allParticipants = [];
        let currentTeamId = null;
        let currentUserProfile = null;
        let currentUserId = null;
        let authToken = localStorage.getItem('fdc_access_token');
        
        function switchTab(tabName, clickedEvent) {{
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            
            const target = clickedEvent && clickedEvent.target ? clickedEvent.target : null;
            if (target) {{
                target.classList.add('active');
            }}
            document.getElementById(tabName).classList.add('active');
            
            if (tabName === 'ranking') loadRanking();
            if (tabName === 'myScore') loadMyScore();
            if (tabName === 'market') loadParticipants();
            
        }}
        
        function logout() {{
            localStorage.removeItem('fdc_access_token');
            window.location.href = '/auth';
        }}

        function updateUserGreeting() {{
            // Estrai name e surname da dove siano disponibili (profile oggetto o radice)
            const profile = (currentUserProfile && currentUserProfile.profile) || currentUserProfile || {{}};
            const name = profile.name || currentUserProfile.name || '';
            const surname = profile.surname || currentUserProfile.surname || '';
            const displayName = (name + ' ' + surname).trim();
            const greeting = displayName && displayName.length > 0 ? 'Ciao, ' + displayName : 'Utente';
            const greetingEl = document.getElementById('userGreeting');
            if (greetingEl) {{
                greetingEl.textContent = greeting;
            }}
        }}

        function renderVolleyStructure(data) {{
            const groupA = (data && data.groups && data.groups.A) ? data.groups.A : [];
            const groupB = (data && data.groups && data.groups.B) ? data.groups.B : [];
            const finals = (data && data.finals) ? data.finals : {{}};

            const renderGroup = (title, teams) => {{
                const rows = teams.length ? teams.map((team, i) => `
                    <tr onclick="showDetailModal(${{JSON.stringify(team).replace(/"/g, '&quot;')}})" style="cursor: pointer;">
                        <td>${{i + 1}}</td>
                        <td>${{team.name || 'Squadra ' + team.id}}</td>
                        <td>${{team.matches_played || 0}}</td>
                        <td>${{team.wins || 0}}</td>
                        <td>${{team.losses || 0}}</td>
                        <td>${{team.sets_won || 0}}</td>
                        <td>${{team.sets_lost || 0}}</td>
                        <td>${{team.points || 0}}</td>
                    </tr>
                `).join('') : '<tr><td colspan="8" style="text-align:center; color:#999;">Nessuna squadra</td></tr>';

                return `
                    <div class="ranking-table">
                        <h3>🏐 ${{title}}</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Pos</th>
                                    <th>Squadra</th>
                                    <th>PF</th>
                                    <th>V</th>
                                    <th>S</th>
                                    <th>SV</th>
                                    <th>SP</th>
                                    <th>Pti</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${{rows}}
                            </tbody>
                        </table>
                    </div>
                `;
            }};

            const formatTeamName = (team) => team ? (team.name || ('Squadra ' + team.id)) : '-';
            const formatScore = (pair) => {{
                if (!pair || !pair.match || !pair.home || !pair.away) return '-';
                const match = pair.match;
                const homeScore = match.home_score ?? 0;
                const awayScore = match.away_score ?? 0;
                return match.home_squad_id === pair.home.id ? `${{homeScore}}-${{awayScore}}` : `${{awayScore}}-${{homeScore}}`;
            }};

            const renderFinalRow = (label, pair) => `
                <tr>
                    <td>${{label}}</td>
                    <td>${{formatTeamName(pair.home)}}</td>
                    <td>${{formatTeamName(pair.away)}}</td>
                    <td>${{formatScore(pair)}}</td>
                </tr>
            `;

            const renderFinalsTable = () => `
                <div class="ranking-table">
                    <h3>🏐 Fasi Finali</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Fase</th>
                                <th>Squadra</th>
                                <th>Squadra</th>
                                <th>Risultato</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${{renderFinalRow('Finale 5/6', finals.fifth_sixth || {{}})}}
                            ${{renderFinalRow('Finale 3/4', finals.third_fourth || {{}})}}
                            ${{renderFinalRow('Finale 1/2', finals.final || {{}})}}
                        </tbody>
                    </table>
                </div>
            `;

            return `
                <div class="volley-container">
                    <div class="volley-tabs">
                        <button class="volley-tab-btn active" onclick="switchVolleyTab(event, 'volley-groupA')">Girone A</button>
                        <button class="volley-tab-btn" onclick="switchVolleyTab(event, 'volley-groupB')">Girone B</button>
                        <button class="volley-tab-btn" onclick="switchVolleyTab(event, 'volley-finals')">Fasi Finali</button>
                    </div>
                    <div id="volley-groupA" class="volley-tab-content active">
                        ${{renderGroup('Girone A', groupA)}}
                    </div>
                    <div id="volley-groupB" class="volley-tab-content">
                        ${{renderGroup('Girone B', groupB)}}
                    </div>
                    <div id="volley-finals" class="volley-tab-content">
                        ${{renderFinalsTable()}}
                    </div>
                </div>
            `;
        }}
        
        function switchVolleyTab(event, tabId) {{
            event.preventDefault();
            
            // Nascondi tutti i tab content
            document.querySelectorAll('.volley-tab-content').forEach(el => {{
                el.classList.remove('active');
            }});
            
            // Rimuovi classe active da tutti i bottoni
            document.querySelectorAll('.volley-tab-btn').forEach(el => {{
                el.classList.remove('active');
            }});
            
            // Mostra il tab selezionato e attiva il bottone
            const tabElement = document.getElementById(tabId);
            if (tabElement) {{
                tabElement.classList.add('active');
            }}
            event.target.classList.add('active');
        }}
        
        async function loadRanking() {{
                try {{
                    const statusEl = document.getElementById('fetchStatus');
                    if (statusEl) statusEl.textContent = 'Caricamento classifica in corso...';
                    console.log('loadRanking: fetching', API_BASE + '/market/ranking', API_BASE + '/market/volley/structure');
                const [rankingRes, volleyRes] = await Promise.all([
                    fetch(`${{API_BASE}}/market/ranking`),
                    fetch(`${{API_BASE}}/market/volley/structure`)
                ]);
                const payload = await rankingRes.json();
                const ranking = Array.isArray(payload) ? payload : [];
                const volleyPayload = volleyRes.ok ? await volleyRes.json() : null;

                if (!rankingRes.ok) {{
                    throw new Error((payload && payload.detail) ? payload.detail : 'Errore caricamento classifica');
                }}

                const sports = ['Calcio', 'Pallavolo', 'Padel'];
                let html = '';

                sports.forEach((sport) => {{
                    const sportRanking = ranking.filter(item => (String(item.sport || item.role || '').toLowerCase() === sport.toLowerCase()));
                    const isCalcio = sport.toLowerCase() === 'calcio';

                    if (sport.toLowerCase() === 'pallavolo' && volleyPayload) {{
                        html += renderVolleyStructure(volleyPayload);
                        return;
                    }}

                    html += `
                        <div class="ranking-table">
                            <h3>🏆 ${{sport}}</h3>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Pos</th>
                                        <th>Squadra</th>
                                        <th>PF</th>
                                        <th>V</th>
                                        <th>S</th>
                                        <th>${{isCalcio ? 'GF' : 'SV'}}</th>
                                        <th>${{isCalcio ? 'GS' : 'SP'}}</th>
                                        ${{isCalcio ? '<th>DR</th>' : ''}}\n                                        <th>Pti</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${{sportRanking.length ? sportRanking.map((team, i) => `
                                        <tr onclick="showDetailModal(${{JSON.stringify(team).replace(/"/g, '&quot;')}})" style="cursor: pointer;">
                                            <td>${{i + 1}}</td>
                                            <td>${{team.name || 'Squadra ' + team.id}}</td>
                                            <td>${{team.matches_played || 0}}</td>
                                            <td>${{team.wins || 0}}</td>
                                            <td>${{team.losses || 0}}</td>
                                            <td>${{isCalcio ? (team.goals_for || 0) : (team.sets_won || 0)}}</td>
                                            <td>${{isCalcio ? (team.goals_against || 0) : (team.sets_lost || 0)}}</td>
                                            ${{isCalcio ? `<td>${{(team.goals_for || 0) - (team.goals_against || 0)}}</td>` : ''}}
                                            <td>${{team.points ?? team.score ?? 0}}</td>
                                        </tr>
                                    `).join('') : `<tr><td colspan="${{isCalcio ? 9 : 8}}" style="text-align:center; color:#999;">Nessuna squadra</td></tr>`}}
                                </tbody>
                            </table>
                        </div>
                    `;
                }});
                
                document.getElementById('rankingContainer').innerHTML = html;
                const statusElDone = document.getElementById('fetchStatus');
                if (statusElDone) statusElDone.textContent = '';
                }} catch (err) {{
                console.error('Errore caricamento ranking:', err);
                const statusEl = document.getElementById('fetchStatus');
                if (statusEl) statusEl.textContent = 'Errore caricamento classifica: ' + (err.message || err);
                document.getElementById('rankingContainer').innerHTML = 
                    '<p style="grid-column: 1/-1; color: #d32f2f;">Errore caricamento classifica</p>';
            }}
        }}
        
        async function loadParticipants() {{
            try {{
                const filterNameEl = document.getElementById('filterName');
                const filterRoleEl = document.getElementById('filterRole');
                const filterCostEl = document.getElementById('filterCost');
                const filterTeamEl = document.getElementById('filterTeam');
                if (filterNameEl) filterNameEl.value = '';
                if (filterRoleEl) filterRoleEl.value = '';
                if (filterCostEl) filterCostEl.value = '100';
                if (filterTeamEl) filterTeamEl.value = '';

                const response = await fetch(`${{API_BASE}}/participants`);
                const payload = await response.json();
                allParticipants = Array.isArray(payload) ? payload : [];
                if (!Array.isArray(payload)) {{
                    console.warn('Risposta partecipanti non valida:', payload);
                }}
                applyFilters();
            }} catch (err) {{
                console.error('Errore caricamento partecipanti:', err);
                const table = document.getElementById('participantsTable');
                if (table) {{
                    table.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: #b91c1c;">Errore nel caricamento dei partecipanti</td></tr>';
                }}
            }}
        }}

        function isOwnedByCurrentUser(participant) {{
            if (!currentUserId) return false;
            const owners = Array.isArray(participant.owner_user_ids) ? participant.owner_user_ids : [];
            return owners.includes(currentUserId);
        }}

        function formatOperationError(response, payload) {{
            const detail = String(payload?.detail || 'Operazione non riuscita');

            if (response.status === 402) {{
                return 'Non hai DomeCoin sufficienti per comprare questa squadra. ' + detail;
            }}
            if (response.status === 401) {{
                return 'Sessione non valida o profilo utente non trovato. Fai di nuovo login. ' + detail;
            }}
            if (response.status === 403) {{
                return 'Operazione non autorizzata per il team selezionato. ' + detail;
            }}
            if (response.status === 404) {{
                return 'Squadra non trovata. ' + detail;
            }}
            if (response.status === 409) {{
                return 'Hai già questa squadra nel tuo roster. ' + detail;
            }}
            if (response.status === 400) {{
                return detail;
            }}

            return detail;
        }}

        async function loadMyScore() {{
            const container = document.getElementById('myScoreContainer');
            if (!container) return;

            if (!authToken) {{
                container.innerHTML = `
                    <h3>Nessun token trovato</h3>
                    <p>Effettua il login per vedere il tuo punteggio.</p>
                `;
                return;
            }}

            try {{
                const response = await fetch(`${{API_BASE}}/users/me`, {{
                    headers: {{ 'Authorization': `Bearer ${{authToken}}` }}
                }});

                if (!response.ok) {{
                    container.innerHTML = `
                        <h3>Impossibile caricare il profilo</h3>
                        <p>Riprova dopo aver effettuato di nuovo il login.</p>
                    `;
                    return;
                }}

                const payload = await response.json();
                currentUserProfile = payload || {{}};
                const profile = (payload && payload.profile) || {{}};
                currentUserId = profile.id || null;

                const teamId = (payload && payload.team_id) || profile.team_id || null;
                currentTeamId = teamId;

                if (!teamId) {{
                    container.innerHTML = `
                        <h3>Team in recupero</h3>
                        <p>Sto riallineando il tuo profilo e il tuo team. Riprova tra pochi secondi.</p>
                    `;
                    updateUserGreeting();
                    return;
                }}

                const rosterResponse = await fetch(`${{API_BASE}}/market/teams/${{teamId}}/roster`);
                const roster = rosterResponse.ok ? await rosterResponse.json() : [];
                const totalScore = roster.reduce((sum, item) => sum + (item.participant_score || 0), 0);
                const listRows = roster.length
                    ? roster.map(item => `
                        <tr>
                            <td>${{item.participant_name || 'N/A'}}</td>
                            <td>${{item.role || '-'}}</td>
                            <td>${{item.participant_score || 0}}</td>
                        </tr>
                    `).join('')
                    : '<tr><td colspan="3" style="opacity:0.8;">Nessun participant acquistato</td></tr>';

                const displayName = ((profile.name || '') + ' ' + (profile.surname || '')).trim();
                const userEmail = payload.email || profile.email || 'N/D';
                const teamName = displayName ? `${{displayName}}'s team` : `Team ${{teamId}}`;

                container.innerHTML = `
                    <h3>${{teamName}}</h3>
                    <p>Account: ${{userEmail}}</p>
                    <div class="score-grid">
                        <div class="score-metric">
                            <span class="label">Punteggio totale</span>
                            <div class="value">${{totalScore}}</div>
                        </div>
                        <div class="score-metric">
                            <span class="label">Participant nel team</span>
                            <div class="value">${{roster.length}}</div>
                        </div>
                    </div>
                    <div class="my-score-list">
                        <table>
                            <thead>
                                <tr>
                                    <th>Participant</th>
                                    <th>Sport</th>
                                    <th>Punti</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${{listRows}}
                            </tbody>
                        </table>
                    </div>
                `;
                updateUserGreeting();
            }} catch (err) {{
                console.error('Errore caricamento punteggio:', err);
                container.innerHTML = `
                    <h3>Errore nel caricamento</h3>
                    <p>Non sono riuscito a recuperare il tuo punteggio.</p>
                `;
            }}
        }}

        function applyFilters() {{
            const name = document.getElementById('filterName').value.toLowerCase();
            const role = document.getElementById('filterRole').value;
            const costMax = parseInt(document.getElementById('filterCost').value) || 100;
            const team = document.getElementById('filterTeam').value.toLowerCase();
            
            const filtered = allParticipants.filter(p => {{
                  return (!name || (p.name || '').toLowerCase().includes(name)) &&
                       (!role || p.role === role) &&
                       (p.cost || 0) <= costMax &&
                       (!team || (p.team_id === parseInt(team) || (p.name || '').toLowerCase().includes(team)));
            }});
            
            const html = filtered.length ? filtered.map(p => `
                <tr>
                    <td>${{allParticipants.indexOf(p) + 1}}</td>
                    <td>${{p.name || 'N/A'}}</td>
                    <td>
                        ${{p.role || 'N/A'}}
                    </td>
                    <td>${{p.score || 0}}</td>
                    <td>${{p.cost || 0}} DomeCoin</td>
                    <td>${{isOwnedByCurrentUser(p) ? 'Nel tuo team' : 'Disponibile'}}</td>
                    <td>
                        ${{isOwnedByCurrentUser(p)
                            ? `<button class="btn btn-sell" onclick="sellParticipant(${{p.id}}, ${{p.cost || 0}}, 'status')">Vendi</button>`
                            : `<button class="btn btn-buy" onclick="buyParticipant(${{p.id}}, ${{p.cost || 0}}, 'status')">Acquista</button>`}}
                    </td>
                </tr>
            `).join('') : '<tr><td colspan="7" style="text-align: center; padding: 20px; color: #999;">Nessun partecipante trovato</td></tr>';
            
            document.getElementById('participantsTable').innerHTML = html;
        }}
        
        async function buyParticipant(participantId, cost, statusTarget) {{
            if (!authToken) {{
                showStatus(statusTarget || 'status', 'Errore: token non trovato. Effettua login prima.', 'error');
                return;
            }}

            if (!currentTeamId) {{
                await loadMyScore();
            }}

            if (!currentTeamId) {{
                showStatus(statusTarget || 'status', 'Team non ancora disponibile. Riprova fra qualche secondo dopo il refresh del profilo.', 'error');
                return;
            }}
            
            try {{
                const response = await fetch(`${{API_BASE}}/market/buy`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${{authToken}}`
                    }},
                    body: JSON.stringify({{
                        buyer_team_id: currentTeamId,
                        participant_id: participantId
                    }})
                }});
                
                const result = await response.json();
                if (response.ok) {{
                    showStatus(statusTarget || 'status', `✓ Acquisto riuscito! Squadra acquistata per ${{cost}} DomeCoin. Non comparirà più nel mercato.`, 'success');
                    loadParticipants();
                    loadMyScore();
                    loadBalance();
                }} else {{
                    showStatus(statusTarget || 'status', `✗ ${{formatOperationError(response, result)}}`, 'error');
                }}
            }} catch (err) {{
                showStatus(statusTarget || 'status', `✗ Errore acquisto: ${{err.message}}`, 'error');
            }}
        }}
        
        async function sellParticipant(participantId, cost, statusTarget) {{
            if (!authToken) {{
                showStatus(statusTarget || 'status', 'Errore: token non trovato. Effettua login prima.', 'error');
                return;
            }}
            
            try {{
                const response = await fetch(`${{API_BASE}}/market/sell`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${{authToken}}`
                    }},
                    body: JSON.stringify({{
                        seller_team_id: currentTeamId,
                        participant_id: participantId
                    }})
                }});
                
                const result = await response.json();
                if (response.ok) {{
                    showStatus(statusTarget || 'status', `✓ Vendita riuscita! Squadra rilasciata e tornata disponibile nel mercato.`, 'success');
                    loadParticipants();
                    loadMyScore();
                    loadBalance();
                }} else {{
                    showStatus(statusTarget || 'status', `✗ ${{formatOperationError(response, result)}}`, 'error');
                }}
            }} catch (err) {{
                showStatus(statusTarget || 'status', `✗ Errore vendita: ${{err.message}}`, 'error');
            }}
        }}
        
        function showStatus(targetId, message, type) {{
            const statusEl = document.getElementById(targetId || 'status');
            if (!statusEl) return;
            statusEl.textContent = message;
            statusEl.className = `status ${{type}}`;
            setTimeout(() => statusEl.className = 'status', 5000);
        }}
        
        
        // Carica classifiche, profilo e saldo DomeCoin al startup
        window.addEventListener('load', async function() {{
            await loadMyScore();
            await loadBalance();
            loadRanking();
        }});

        // Carica e mostra il saldo DomeCoin dell'utente
        async function loadBalance() {{
            const el = document.getElementById('domeBalance');
            if (!el) return;
            if (!authToken) {{
                el.textContent = 'DomeCoin: —';
                return;
            }}

            try {{
                const resp = await fetch(`${{API_BASE}}/users/me`, {{ headers: {{ 'Authorization': `Bearer ${{authToken}}` }} }});
                if (!resp.ok) {{
                    el.textContent = 'DomeCoin: —';
                    return;
                }}
                const payload = await resp.json();
                const profile = payload?.profile || {{}};
                const raw = profile?.dome_balance ?? payload?.dome_balance ?? profile?.balance ?? payload?.balance ?? 0;
                const num = Number(raw) || 0;
                const formatted = num.toLocaleString('it-IT', {{ minimumFractionDigits: 0, maximumFractionDigits: 2 }});
                el.textContent = `DomeCoin: ${{formatted}}`;
            }} catch (err) {{
                console.warn('Impossibile caricare DomeCoin:', err);
                el.textContent = 'DomeCoin: —';
            }}
        }}
        
        function showDetailModal(team) {{
            if (!team || !team.id) return;
            
            const isCalcio = (team.sport || team.role || '').toLowerCase() === 'calcio';
            const title = team.name || ('Squadra ' + team.id);
            
            let statsHtml = '';
            if (isCalcio) {{
                const diffReti = (team.goals_for || 0) - (team.goals_against || 0);
                statsHtml = `
                    <div class="modal-stats">
                        <div class="modal-stat-box">
                            <div class="modal-stat-label">Gol Fatti</div>
                            <div class="modal-stat-value">${{team.goals_for || 0}}</div>
                        </div>
                        <div class="modal-stat-box">
                            <div class="modal-stat-label">Gol Subiti</div>
                            <div class="modal-stat-value">${{team.goals_against || 0}}</div>
                        </div>
                        <div class="modal-stat-box">
                            <div class="modal-stat-label">Differenza Reti</div>
                            <div class="modal-stat-value" style="color: ${{diffReti > 0 ? '#10b981' : diffReti < 0 ? '#ef4444' : '#666'}};">${{diffReti > 0 ? '+' : ''}}${{diffReti}}</div>
                        </div>
                        <div class="modal-stat-box">
                            <div class="modal-stat-label">Partite Giocate</div>
                            <div class="modal-stat-value">${{team.matches_played || 0}}</div>
                        </div>
                    </div>
                    <div class="modal-info">
                        <strong>Punteggio totale:</strong> ${{team.points ?? team.score ?? 0}} punti (3 per vittoria, 1 per pareggio, 0 per sconfitta)
                    </div>
                `;
            }} else {{
                statsHtml = `
                    <div class="modal-stats">
                        <div class="modal-stat-box">
                            <div class="modal-stat-label">Set Vinti</div>
                            <div class="modal-stat-value">${{team.sets_won || 0}}</div>
                        </div>
                        <div class="modal-stat-box">
                            <div class="modal-stat-label">Set Persi</div>
                            <div class="modal-stat-value">${{team.sets_lost || 0}}</div>
                        </div>
                        <div class="modal-stat-box">
                            <div class="modal-stat-label">Partite Giocate</div>
                            <div class="modal-stat-value">${{team.matches_played || 0}}</div>
                        </div>
                        <div class="modal-stat-box">
                            <div class="modal-stat-label">Punteggio</div>
                            <div class="modal-stat-value">${{team.points ?? team.score ?? 0}}</div>
                        </div>
                    </div>
                    <div class="modal-info">
                        <strong>Sport:</strong> ${{team.sport || team.role || 'N/A'}}<br>
                        <strong>Punti per vittoria:</strong> 1 punto
                    </div>
                `;
            }}
            
            let composedOfHtml = '';
            if (team.composed_of) {{
                const players = team.composed_of.split(',').map(p => p.trim()).filter(p => p);
                if (players.length > 0) {{
                    composedOfHtml = `
                        <div class="modal-info">
                            <strong>🏐 Composto da:</strong><br>
                            <div style="margin-top: 8px; padding: 10px; background: rgba(124, 58, 237, 0.1); border-radius: 6px;">
                                ${{players.map(p => `<div style="padding: 4px 0;">• ${{p}}</div>`).join('')}}
                            </div>
                        </div>
                    `;
                }}
            }}
            
            const modalBody = `
                ${{statsHtml}}
                <div class="modal-info">
                    <strong>Costo:</strong> ${{team.total_cost || 0}} DomeCoin
                </div>
                ${{composedOfHtml}}
            `;
            document.getElementById('modalTitle').textContent = title;
            document.getElementById('modalBody').innerHTML = modalBody;
            document.getElementById('detailModal').style.display = 'block';
        }}
        
        function closeDetailModal() {{
            document.getElementById('detailModal').style.display = 'none';
        }}
        
        window.addEventListener('click', function(event) {{
            const modal = document.getElementById('detailModal');
            if (event.target === modal) {{
                closeDetailModal();
            }}
        }});
    </script>
</body>
</html>
"""
    
    return HTMLResponse(content=html)
