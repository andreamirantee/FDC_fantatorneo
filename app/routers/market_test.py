"""Home con classifica, risultato finale e filtri partecipanti.

Interfaccia HTML interattiva per testare transazioni:
- Accessibile SOLO dopo login riuscito su auth-test
- Visualizzazione classifica (ranking) con 3 sport
- Filtri per partecipanti (ruolo, costo, team)
- Bottoni per buy/sell operazioni mercato
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from ..auth import get_current_user

router = APIRouter(tags=["Home"], include_in_schema=False)


@router.get("/home")
def serve_home():
    """Pagina HTML interattiva home con classifica e mercato.
    
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
    <title>FDCFANTA ✦ Mercato Fantasy - Test</title>
    <style>
        :root {{
            --theme-sky: #33ccff;
            --theme-pink: #ff80a8;
            --theme-yellow: #ffd24d;
            --theme-ink: #102033;
            --theme-surface: #ffffff;
            --theme-muted: #f7fbff;
            --theme-border: rgba(16, 32, 51, 0.14);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background:
                radial-gradient(circle at top left, rgba(51, 204, 255, 0.12), transparent 36%),
                radial-gradient(circle at top right, rgba(255, 128, 168, 0.10), transparent 32%),
                radial-gradient(circle at bottom center, rgba(255, 210, 77, 0.08), transparent 34%),
                #1a2333;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1560px;
            margin: 0 auto;
            background: rgba(40, 54, 78, 0.92);
            color: #eef3fb;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.18);
            box-shadow: 0 24px 80px rgba(0,0,0,0.38);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 52%, var(--theme-yellow) 100%);
            color: #102033;
            padding: 30px;
            display: block;
        }}
        .header-left {{
            text-align: center;
            margin-bottom: 18px;
        }}
        .header-left h1 {{
            font-size: clamp(3.2rem, 7vw, 6rem);
            margin-bottom: 8px;
            line-height: 0.95;
            letter-spacing: 0.05em;
            font-weight: 900;
            color: #0b1b2d;
            text-shadow: 0 6px 20px rgba(255, 255, 255, 0.45);
        }}
        .header-left p {{ opacity: 0.95; font-weight: 700; }}
        .header-right {{
            text-align: right;
            background: rgba(255,255,255,0.10);
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
            color: #ffffff;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
            min-width: 140px;
            text-align: right;
        }}
        .user-greeting {{
            font-size: 13px;
            opacity: 0.9;
            white-space: nowrap;
        }}
        .btn-logout {{
            background: linear-gradient(135deg, var(--theme-pink) 0%, #ff9ac0 100%);
            color: #102033;
            border: 1px solid rgba(16, 32, 51, 0.08);
            padding: 8px 16px;
            border-radius: 999px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 700;
            box-shadow: 0 8px 18px rgba(16, 32, 51, 0.12);
        }}
        .btn-logout:hover {{ background: linear-gradient(135deg, #ff8eb5 0%, #ffb4d0 100%); }}
        .protected-badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.22);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }}
        
        .content {{
            display: block;
            min-height: 600px;
            padding: 16px;
        }}
        
        .panel {{
            flex: 1;
            padding: 48px;
            display: block;
            overflow-y: auto;
            margin-bottom: 28px;
            background: rgba(30, 43, 64, 0.92);
            border: 1px solid rgba(255,255,255,0.16);
            border-radius: 20px;
            box-shadow: 0 18px 50px rgba(0,0,0,0.22);
        }}
        .panel.active {{ display: block; }}
        
        .ranking-container {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }}
        .panel#ranking {{
            margin-top: 0;
            width: 100%;
        }}
        .ranking-table {{
            background: #324765;
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 8px;
            overflow: hidden;
        }}
        .ranking-table h3 {{
            background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 55%, var(--theme-yellow) 100%);
            color: #102033;
            padding: 15px;
            margin: 0;
        }}
        .ranking-table table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .ranking-table th {{
            background: rgba(255, 255, 255, 0.14);
            padding: 10px;
            text-align: left;
            font-size: 12px;
            font-weight: 600;
            color: #eef3fb;
        }}
        .ranking-table td {{
            padding: 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.12);
            color: #dce6f7;
        }}
        .ranking-table td:nth-child(2) {{
            text-align: center;
        }}
        .ranking-table tr:hover {{ background: rgba(51, 204, 255, 0.08); }}
        
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
            color: var(--theme-sky);
            border-bottom-color: var(--theme-sky);
        }}
        .volley-tab-content {{
            display: none;
        }}
        .volley-tab-content.active {{
            display: block;
        }}

        .score-card {{
            background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 55%, var(--theme-yellow) 100%);
            color: #102033;
            border-radius: 16px;
            padding: 28px;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
        }}
        .score-card h3 {{
            font-size: 28px;
            margin-bottom: 8px;
        }}
        .score-card p {{
            color: rgba(16, 32, 51, 0.86);
            line-height: 1.5;
        }}
        .score-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-top: 22px;
        }}
        .score-metric {{
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.14);
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
            background: rgba(255,255,255,0.10);
            color: #102033;
            overflow: hidden;
        }}
        .my-score-list table {{
            width: 100%;
            border-collapse: collapse;
            color: #102033;
        }}
        .my-score-list th,
        .my-score-list td {{
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255,255,255,0.12);
            text-align: left;
            font-size: 13px;
            color: #102033;
        }}
        .my-score-list td {{
            color: #102033;
        }}
        .my-score-list h4 {{
            padding: 12px;
            margin: 0;
            font-size: 15px;
            color: #102033;
            background: rgba(255,255,255,0.14);
        }}

        .market-composed {{
            margin-top: 8px;
            padding: 12px 14px;
            background: linear-gradient(135deg, rgba(51, 204, 255, 0.18) 0%, rgba(255, 128, 168, 0.14) 55%, rgba(255, 210, 77, 0.18) 100%);
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.14);
            line-height: 1.55;
            color: #eef3fb;
            font-size: 15px;
            font-weight: 800;
            white-space: nowrap;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            min-height: 48px;
            display: flex;
            align-items: center;
        }}
        .market-composed span {{
            display: inline;
            color: #eef3fb;
        }}
        .market-participant-role {{
            font-size: 13px;
            color: #b9c9e6;
            margin-top: 6px;
        }}

        .market-card {{
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 14px;
            display: grid;
            grid-template-columns: minmax(0, 1fr) 220px;
            gap: 16px;
            background: linear-gradient(180deg, rgba(55, 72, 99, 0.98) 0%, rgba(41, 57, 82, 0.98) 100%);
            box-shadow: 0 14px 30px rgba(8, 15, 28, 0.18);
        }}
        .market-card-title {{
            font-weight: 800;
            font-size: 17px;
            color: #ffffff;
            letter-spacing: 0.01em;
        }}
        .market-card-subtitle {{
            font-size: 13px;
            color: #b9c9e6;
            margin-top: 6px;
        }}
        .market-card-cost {{
            font-weight: 800;
            font-size: 16px;
            color: var(--theme-yellow);
            text-shadow: 0 0 10px rgba(255, 210, 77, 0.20);
        }}
        .market-card-actions {{
            text-align: right;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            gap: 10px;
        }}

        .my-score-list th {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            opacity: 0.8;
            color: #102033;
        }}
        
        .filters {{
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.18);
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
            color: var(--theme-pink);
            margin-bottom: 5px;
        }}
        .filter-group input,
        .filter-group select {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid rgba(255, 255, 255, 0.24);
            background: rgba(58, 76, 104, 0.92);
            color: #eef3fb;
            border-radius: 4px;
            font-size: 13px;
        }}
        
        .participants-table {{
            width: 100%;
            border-collapse: collapse;
            background: #344a69;
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 8px;
            overflow: hidden;
        }}
        .participants-table th {{
            background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 55%, var(--theme-yellow) 100%);
            color: #102033;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        .participants-table td {{
            padding: 12px 15px;
            border-top: 1px solid rgba(255, 255, 255, 0.10);
            color: #dce6f7;
        }}
        .participants-table tr:hover {{ background: rgba(255, 128, 168, 0.10); }}
        
        .btn {{
            padding: 10px 16px;
            border: 1px solid rgba(16, 32, 51, 0.12);
            border-radius: 999px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.01em;
            transition: transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease, color 0.18s ease;
            box-shadow: 0 8px 18px rgba(16, 32, 51, 0.12);
        }}
        .btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 12px 24px rgba(16, 32, 51, 0.16);
        }}
        .btn:active {{ transform: translateY(0); }}
        .btn-buy {{
            background: linear-gradient(135deg, var(--theme-sky) 0%, #63d9ff 100%);
            color: #102033;
        }}
        .btn-buy:hover {{ background: linear-gradient(135deg, #45d1ff 0%, #7de2ff 100%); }}
        .btn-sell {{
            background: linear-gradient(135deg, var(--theme-pink) 0%, #ff9ac0 100%);
            color: #102033;
        }}
        .btn-sell:hover {{ background: linear-gradient(135deg, #ff8eb5 0%, #ffb0ce 100%); }}
        .btn-go-market {{
            background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 52%, var(--theme-yellow) 100%);
            color: #102033;
            padding: 14px 30px;
            margin-top: 20px;
            font-size: 15px;
        }}
        .btn-go-market:hover {{ background: linear-gradient(135deg, #45d1ff 0%, #ff92b8 70%, #ffe17d 100%); }}
        .btn-buy-section {{
            background: linear-gradient(135deg, var(--theme-yellow) 0%, #ffe17d 100%);
            color: #102033;
            padding: 12px 30px;
            margin-top: 20px;
            font-size: 14px;
        }}
        .btn-buy-section:hover {{ background: linear-gradient(135deg, #ffe27c 0%, #ffedb4 100%); }}
        
        .status {{
            margin-top: 20px;
            padding: 15px;
            border-radius: 4px;
            display: none;
        }}
        .status.success {{ background: #d1fae5; color: #065f46; border: 1px solid #6ee7b7; display: block; }}
        .status.error {{ background: #ffe3ea; color: #a11546; border: 1px solid #ffb3c7; display: block; }}
        .status.info {{ background: #e6fbff; color: #0c2d6b; border: 1px solid #99e6ff; display: block; }}
        
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
            background: #1f2a3d;
            color: #eef3fb;
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
            border-bottom: 2px solid var(--theme-sky);
            padding-bottom: 15px;
        }}
        .modal-header h2 {{
            margin: 0;
            color: #eef3fb;
        }}
        .modal-close {{
            font-size: 28px;
            font-weight: bold;
            color: #dce6f7;
            cursor: pointer;
            line-height: 20px;
        }}
        .modal-close:hover {{
            color: #fff;
        }}
        .modal-stats {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}
        .modal-stat-box {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .modal-stat-label {{
            font-size: 12px;
            font-weight: 600;
            color: rgba(238, 243, 251, 0.72);
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .modal-stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: var(--theme-pink);
        }}
        .modal-info {{
            background: rgba(255, 210, 77, 0.08);
            border-left: 4px solid var(--theme-yellow);
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
            font-size: 13px;
            color: #eef3fb;
        }}

        #filterName {{
            text-align: center !important;
        }}
        
        #filterName::placeholder {{
            text-align: center;
        }}

        @media (max-width: 1024px) {{
            body {{ padding: 12px; }}
            .container {{ border-radius: 16px; }}
            .header {{ padding: 22px; }}
            .header-left {{ margin-bottom: 14px; }}
            .header-left h1 {{ font-size: clamp(2.4rem, 9vw, 4rem); line-height: 1; }}
            .header-right {{ width: 100%; justify-content: space-between; flex-wrap: wrap; }}
            .content {{ min-height: auto; }}
            .panel {{ padding: 20px; }}
            .filters {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .score-grid {{ grid-template-columns: 1fr; }}
            .modal-content {{ width: 94%; margin: 8% auto; padding: 20px; }}
            .modal-stats {{ grid-template-columns: 1fr 1fr; gap: 12px; }}
        }}

        @media (max-width: 640px) {{
            body {{ padding: 8px; }}
            .container {{ border-radius: 14px; }}
            .header {{ padding: 16px; }}
            .header-left h1 {{ font-size: clamp(2rem, 10vw, 2.8rem); }}
            .header-left p {{ font-size: 13px; }}
            .header-right {{ flex-direction: column; align-items: stretch; gap: 10px; }}
            .user-greeting, .dome-balance {{ width: 100%; text-align: left; min-width: 0; }}
            .btn-logout {{ width: 100%; min-height: 44px; }}
            .panel {{ padding: 16px; }}
            .panel h2 {{ font-size: 1.25rem; }}
            .ranking-table, .my-score-list, .participants-table {{ display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
            .ranking-table th, .ranking-table td, .my-score-list th, .my-score-list td, .participants-table th, .participants-table td {{ padding: 10px 8px; font-size: 12px; }}
            .filters {{ grid-template-columns: 1fr; gap: 10px; padding: 14px; }}
            .filter-group input,
            .filter-group select,
            #sportSelector,
            #sportSelect {{ width: 100%; min-height: 44px; font-size: 16px; }}
            .market-card {{ grid-template-columns: 1fr; gap: 12px; padding: 14px; }}
            .market-card-actions {{ text-align: left; }}
            .market-card-cost {{ font-size: 18px; }}
            .market-card-title {{ font-size: 18px; line-height: 1.2; }}
            .market-card-subtitle {{ font-size: 14px; line-height: 1.35; }}
            .market-composed {{ font-size: 16px; line-height: 1.6; min-height: 52px; padding: 12px 14px; white-space: normal; overflow-x: visible; }}
            .market-composed span {{ display: inline; }}
            .btn, .btn-go-market, .btn-buy-section {{ width: 100%; min-height: 44px; padding: 12px 16px; }}
            .score-card {{ padding: 18px; border-radius: 14px; }}
            .score-card h3 {{ font-size: 1.45rem; }}
            .modal-content {{ width: 96%; margin: 6% auto; padding: 16px; }}
            .modal-header {{ gap: 12px; }}
            .modal-stats {{ grid-template-columns: 1fr; gap: 12px; }}
            .modal-stat-value {{ font-size: 22px; }}
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
                <h1>FDCFANTA ✦</h1>
                <p>🏠 Home Fantatorneo <span class="protected-badge">🔐 Protetto</span></p>
            </div>
            <div class="header-right">
                <div class="user-greeting">👤 <span id="userGreeting">Caricamento...</span></div>
                <div id="domeBalance" class="dome-balance">DomeCoin: —</div>
                <button class="btn-logout" onclick="logout()">Esci</button>
            </div>
        </div>
        
        <div class="content">
            <div class="panel active" id="ranking">
                <div style="margin-bottom: 20px;">
                    <label for="sportSelector" style="font-weight: 600; color: #eef3fb; margin-right: 10px;">Seleziona Sport:</label>
                    <select id="sportSelector" onchange="renderRankingBySport(this.value)" style="padding: 8px 12px; border: 1px solid rgba(255,255,255,0.14); background: rgba(17,24,39,0.92); color: #eef3fb; border-radius: 6px; font-size: 14px; cursor: pointer;">
                        <option value="Calcio">⚽ Calcio</option>
                        <option value="Pallavolo">🏐 Pallavolo</option>
                        <option value="Padel">🎾 Padel</option>
                    </select>
                </div>
                <div class="ranking-container" id="rankingContainer">
                    <div style="text-align: center; grid-column: 1/-1; padding: 40px; color: rgba(238,243,251,0.72);">
                        Caricamento classifica...
                    </div>
                </div>
                <div id="fetchStatus" style="padding:10px 20px; color:#b91c1c; font-weight:700;"></div>
                <button class="btn-go-market" onclick="switchTab('myScore')">→ Vai al mio punteggio</button>
            </div>

            <div class="panel" id="myScore">
                <div class="score-card" id="myScoreContainer">
                    <h3>Caricamento punteggio...</h3>
                    <p>Sto recuperando il tuo team e il relativo punteggio.</p>
                </div>

                <button class="btn-go-market" onclick="switchTab('ranking')">→ Torna alle classifiche</button>
            </div>

            <div class="panel" id="finalStandings">
                <div id="finalStandingsContainer" style="background: linear-gradient(135deg, var(--theme-sky) 0%, var(--theme-pink) 55%, var(--theme-yellow) 100%); color: #102033; border-radius: 16px; padding: 28px; margin-bottom: 20px;">
                    <p>Caricamento classifica finale...</p>
                </div>
                
                <div class="ranking-table" id="finalStandingsTable">
                    <div id="finalTableContent" style="padding: 20px; text-align: center; color: rgba(238,243,251,0.72);">
                        Caricamento...
                    </div>
                </div>

                <button class="btn-go-market" onclick="switchTab('myScore')">→ Torna al mio punteggio</button>
            </div>

            <div class="panel" id="market">
                <div style="display:flex; gap:12px; align-items:center; margin-bottom:16px; flex-wrap:wrap; justify-content:center;">
                    <select id="sportSelect" onchange="renderMarketBySport()" onfocus="prepareMarketSportSelect(this)" style="background: rgba(58,76,104,0.92); color:#eef3fb; border:1px solid rgba(255,255,255,0.24); border-radius:8px; min-height:40px; min-width:220px; padding:8px 12px; font-weight:700;">
                        <option value="all">Seleziona Sport</option>
                        <option value="Calcio">Calcio</option>
                        <option value="Pallavolo">Pallavolo</option>
                        <option value="Padel">Padel</option>
                    </select>
                    <input type="text" id="filterName" placeholder="Cerca nome partecipante" oninput="renderMarketBySport()" style="padding:8px 10px; border:1px solid rgba(255,255,255,0.24); background: rgba(58,76,104,0.92); color:#eef3fb; border-radius:8px; min-height:40px; min-width:260px; text-align:center;" />
                </div>

                <div id="marketList">
                    <div style="text-align: center; padding: 20px; color: rgba(238,243,251,0.72);">Caricamento partecipanti...</div>
                </div>
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
        let currentDomeBalance = 0;
        let authToken = localStorage.getItem('fdc_access_token');
        let currentFase = parseInt(localStorage.getItem('tournamentFase') || '1'); // Default fase 1
        
        // Applica logica di visibilità in base alla fase del torneo
        function applyFaseLogic() {{
            currentFase = parseInt(localStorage.getItem('tournamentFase') || '1');
            const rankingBtn = Array.from(document.querySelectorAll('.tab-btn')).find(btn => btn.textContent.includes('Classifica'));
            const myScoreBtn = Array.from(document.querySelectorAll('.tab-btn')).find(btn => btn.textContent.includes('punteggio'));
            const finalStandingsBtn = Array.from(document.querySelectorAll('.tab-btn')).find(btn => btn.textContent.includes('Risultato'));
            const marketBtn = Array.from(document.querySelectorAll('.tab-btn')).find(btn => btn.textContent.includes('Mercato'));
            
            const rankingPanel = document.getElementById('ranking');
            const myScorePanel = document.getElementById('myScore');
            const finalStandingsPanel = document.getElementById('finalStandings');
            const marketPanel = document.getElementById('market');
            
            // Fase 1: Visibile tutto tranne risultato finale
            if (currentFase === 1) {{
                if (rankingBtn) rankingBtn.style.display = 'inline-block';
                if (myScoreBtn) myScoreBtn.style.display = 'inline-block';
                if (finalStandingsBtn) finalStandingsBtn.style.display = 'none';
                if (marketBtn) marketBtn.style.display = 'inline-block';
                if (rankingPanel) rankingPanel.style.display = 'block';
                if (myScorePanel) myScorePanel.style.display = 'block';
                if (finalStandingsPanel) finalStandingsPanel.style.display = 'none';
                if (marketPanel) marketPanel.style.display = 'block';
                // Attiva ranking se finalStandings era attivo
                const activeTab = document.querySelector('.tab-btn.active');
                if (activeTab && activeTab.textContent.includes('Risultato')) {{
                    if (rankingBtn) rankingBtn.click();
                }}
            }}
            // Fase 2: Mostra solo ranking e myScore
            else if (currentFase === 2) {{
                if (rankingBtn) rankingBtn.style.display = 'inline-block';
                if (myScoreBtn) myScoreBtn.style.display = 'inline-block';
                if (finalStandingsBtn) finalStandingsBtn.style.display = 'none';
                if (marketBtn) marketBtn.style.display = 'none';
                if (rankingPanel) rankingPanel.style.display = 'block';
                if (myScorePanel) myScorePanel.style.display = 'block';
                if (finalStandingsPanel) finalStandingsPanel.style.display = 'none';
                if (marketPanel) marketPanel.style.display = 'none';
                // Attiva ranking se market o finalStandings era attivo
                const activeTab = document.querySelector('.tab-btn.active');
                if (activeTab && (activeTab.textContent.includes('Mercato') || activeTab.textContent.includes('Risultato'))) {{
                    if (rankingBtn) rankingBtn.click();
                }}
            }}
            // Fase 3: Mostra solo risultato finale
            else if (currentFase === 3) {{
                if (rankingBtn) rankingBtn.style.display = 'none';
                if (myScoreBtn) myScoreBtn.style.display = 'none';
                if (finalStandingsBtn) finalStandingsBtn.style.display = 'inline-block';
                if (marketBtn) marketBtn.style.display = 'none';
                if (rankingPanel) rankingPanel.style.display = 'none';
                if (myScorePanel) myScorePanel.style.display = 'none';
                if (finalStandingsPanel) finalStandingsPanel.style.display = 'block';
                if (marketPanel) marketPanel.style.display = 'none';
                // Attiva finalStandings
                if (finalStandingsBtn) finalStandingsBtn.click();
            }}
        }}
        
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
            if (tabName === 'finalStandings') loadFinalStandings();
            if (tabName === 'market') loadParticipants();

            const targetPanel = document.getElementById(tabName);
            if (targetPanel) {{
                setTimeout(() => {{
                    targetPanel.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}, 0);
            }}
            
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
                        <td>${{team.draws || 0}}</td>
                        <td>${{team.losses || 0}}</td>
                        <td>${{team.sets_won || 0}}</td>
                        <td>${{team.sets_lost || 0}}</td>
                        <td>${{team.points || 0}}</td>
                    </tr>
                `).join('') : '<tr><td colspan="9" style="text-align:center; color:#999;">Nessuna squadra</td></tr>';

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
                                    <th>P</th>
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
                    console.log('loadRanking: fetching ranking and structures');
                const [rankingRes, calcioRes, volleyRes, padelRes] = await Promise.all([
                    fetch(`${{API_BASE}}/market/ranking`),
                    fetch(`${{API_BASE}}/market/structure/calcio`),
                    fetch(`${{API_BASE}}/market/structure/volley`),
                    fetch(`${{API_BASE}}/market/structure/padel`)
                ]);
                const payload = await rankingRes.json();
                window.globalRanking = Array.isArray(payload) ? payload : [];
                window.globalCalcioStructure = calcioRes.ok ? await calcioRes.json() : null;
                window.globalVolleyPayload = volleyRes.ok ? await volleyRes.json() : null;
                window.globalPadelStructure = padelRes.ok ? await padelRes.json() : null;

                if (!rankingRes.ok) {{
                    throw new Error((payload && payload.detail) ? payload.detail : 'Errore caricamento classifica');
                }}

                // Renderizza il primo sport (Calcio) di default
                renderRankingBySport('Calcio');
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
        
        function renderRankingBySport(sport) {{
            const ranking = window.globalRanking || [];
            let html = '';
            const sportKey = sport.toLowerCase();
            
            // Scegli la struttura giusta in base allo sport
            let structure = null;
            if (sportKey === 'pallavolo') {{
                structure = window.globalVolleyPayload;
            }} else if (sportKey === 'calcio') {{
                structure = window.globalCalcioStructure;
            }} else if (sportKey === 'padel') {{
                structure = window.globalPadelStructure;
            }}
            
            // Se esiste una struttura con gironi e fasi finali, renderizzala con i tab
            if (structure && structure.groups) {{
                html = renderSportStructure(sport, structure);
            }} else {{
                // Altrimenti mostra la classifica semplice
                const sportRanking = ranking.filter(item => (String(item.sport || item.role || '').toLowerCase() === sportKey));
                const isCalcio = sportKey === 'calcio';
                
                html = `
                    <div class="ranking-table">
                        <h3>🏆 ${{sport}}</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Pos</th>
                                    <th>Squadra</th>
                                    <th>PF</th>
                                    <th>V</th>
                                    <th>P</th>
                                    <th>S</th>
                                    <th>${{isCalcio ? 'GF' : 'SV'}}</th>
                                    <th>${{isCalcio ? 'GS' : 'SP'}}</th>
                                    ${{isCalcio ? '<th>DR</th>' : ''}}
                                    <th>Pti</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${{sportRanking.length ? sportRanking.map((team, i) => `
                                    <tr onclick="showDetailModal(${{JSON.stringify(team).replace(/"/g, '&quot;')}})" style="cursor: pointer;">
                                        <td>${{i + 1}}</td>
                                        <td>${{team.name || 'Squadra ' + team.id}}</td>
                                        <td>${{team.matches_played || 0}}</td>
                                        <td>${{team.wins || 0}}</td>
                                        <td>${{team.draws || 0}}</td>
                                        <td>${{team.losses || 0}}</td>
                                        <td>${{isCalcio ? (team.goals_for || 0) : (team.sets_won || 0)}}</td>
                                        <td>${{isCalcio ? (team.goals_against || 0) : (team.sets_lost || 0)}}</td>
                                        ${{isCalcio ? `<td>${{(team.goals_for || 0) - (team.goals_against || 0)}}</td>` : ''}}
                                        <td>${{team.points ?? team.score ?? 0}}</td>
                                    </tr>
                                `).join('') : `<tr><td colspan="${{isCalcio ? 10 : 9}}" style="text-align:center; color:#999;">Nessuna squadra</td></tr>`}}
                            </tbody>
                        </table>
                    </div>
                `;
            }}
            
            document.getElementById('rankingContainer').innerHTML = html;
        }}
        
        function renderSportStructure(sport, data) {{
            const sportKey = sport.toLowerCase();
            const icons = {{
                'calcio': '⚽',
                'pallavolo': '🏐',
                'padel': '🎾'
            }};
            const icon = icons[sportKey] || '🏆';
            
            const groupA = (data && data.groups && data.groups.A) ? data.groups.A : [];
            const groupB = (data && data.groups && data.groups.B) ? data.groups.B : [];
            const finals = (data && data.finals) ? data.finals : {{}};
            
            const isCalcio = sportKey === 'calcio';
            const isPadel = sportKey === 'padel';

            const renderGroup = (title, teams) => {{
                const rows = teams.length ? teams.map((team, i) => `
                    <tr onclick="showDetailModal(${{JSON.stringify(team).replace(/"/g, '&quot;')}})" style="cursor: pointer;">
                        <td>${{i + 1}}</td>
                        <td>${{team.name || 'Squadra ' + team.id}}</td>
                        <td>${{team.matches_played || 0}}</td>
                        <td>${{team.wins || 0}}</td>
                        <td>${{team.draws || 0}}</td>
                        <td>${{team.losses || 0}}</td>
                        <td>${{isCalcio ? (team.goals_for || 0) : isPadel ? (team.sets_won || 0) : (team.sets_won || 0)}}</td>
                        <td>${{isCalcio ? (team.goals_against || 0) : isPadel ? (team.sets_lost || 0) : (team.sets_lost || 0)}}</td>
                        ${{isCalcio ? `<td>${{(team.goals_for || 0) - (team.goals_against || 0)}}</td>` : ''}}
                        <td>${{team.points || 0}}</td>
                    </tr>
                `).join('') : '<tr><td colspan="' + (isCalcio ? 10 : 9) + '" style="text-align:center; color:#999;">Nessuna squadra</td></tr>';

                return `
                    <div class="ranking-table">
                        <h3>${{icon}} ${{title}}</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Pos</th>
                                    <th>Squadra</th>
                                    <th>PF</th>
                                    <th>V</th>
                                    <th>P</th>
                                    <th>S</th>
                                    <th>${{isCalcio ? 'GF' : 'SV'}}</th>
                                    <th>${{isCalcio ? 'GS' : 'SP'}}</th>
                                    ${{isCalcio ? '<th>DR</th>' : ''}}
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
                    <h3>${{icon}} Fasi Finali</h3>
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
        
        async function loadFinalStandings() {{
            const container = document.getElementById('finalStandingsContainer');
            const tableContainer = document.getElementById('finalTableContent');
            
            if (!container || !tableContainer) return;
            
            try {{
                // Carica i team
                const teamsResponse = await fetch(`${{API_BASE}}/teams`);
                const teamsPayload = teamsResponse.ok ? await teamsResponse.json() : [];
                const teams = Array.isArray(teamsPayload) ? teamsPayload : [];
                
                // Carica ranking per ottenere score aggiornato
                const rankingResponse = await fetch(`${{API_BASE}}/market/ranking`);
                const rankingPayload = rankingResponse.ok ? await rankingResponse.json() : [];
                const ranking = Array.isArray(rankingPayload) ? rankingPayload : [];
                
                // Crea mappa score -> team
                const scoreMap = new Map();
                ranking.forEach(item => {{
                    if (item.id) {{
                        scoreMap.set(Number(item.id), Number(item.score || item.points || 0));
                    }}
                }});
                
                // Ordina team per score decrescente
                const sortedTeams = teams
                    .map(t => ({{
                        id: t.id,
                        name: t.name || `Team ${{t.id}}`,
                        score: scoreMap.get(Number(t.id)) || 0
                    }}))
                    .sort((a, b) => b.score - a.score);
                
                // Trova posizione utente
                const userPosition = sortedTeams.findIndex(t => Number(t.id) === Number(currentTeamId));
                const userTeam = userPosition >= 0 ? sortedTeams[userPosition] : null;
                
                // Mostra posizione utente in card
                if (userTeam && userPosition >= 0) {{
                    const medal = userPosition === 0 ? '🥇' : userPosition === 1 ? '🥈' : userPosition === 2 ? '🥉' : userPosition + 1;
                    container.innerHTML = `
                        <div style="text-align: center;">
                            <h3 style="font-size: 32px; margin: 0 0 10px 0;">Sei arrivato in posizione <strong>#${{userPosition + 1}}</strong></h3>
                            <p style="font-size: 18px; margin: 10px 0;">${{userTeam.name}}</p>
                            <div class="score-grid" style="max-width: 400px; margin: 20px auto;">
                                <div class="score-metric">
                                    <span class="label">Posizione</span>
                                    <div class="value" style="font-size: 48px;">${{medal}}</div>
                                </div>
                                <div class="score-metric">
                                    <span class="label">Punteggio finale</span>
                                    <div class="value">${{userTeam.score}}</div>
                                </div>
                            </div>
                        </div>
                    `;
                }} else {{
                    container.innerHTML = '<p style="text-align: center; opacity: 0.8;">Posizione non trovata</p>';
                }}
                
                // Mostra classifica completa
                const tableHtml = `
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: rgba(255,255,255,0.07);">
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #eef3fb;">Posizione</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #eef3fb;">Team</th>
                                <th style="padding: 12px; text-align: right; font-weight: 600; color: #eef3fb;">Punteggio</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${{sortedTeams.map((team, i) => {{
                                const isCurrentUser = Number(team.id) === Number(currentTeamId);
                                const rowStyle = isCurrentUser 
                                    ? 'background: #e0e0ff; font-weight: 700;'
                                    : 'background: rgba(255,255,255,0.02);';
                                const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : (i + 1);
                                return `
                                    <tr style="${{rowStyle}} border-top: 1px solid #eee; ${{isCurrentUser ? 'border-left: 4px solid var(--theme-sky);' : ''}}" ${{isCurrentUser ? 'title="Il tuo team"' : ''}}>
                                        <td style="padding: 12px; text-align: left;">${{medal}}</td>
                                        <td style="padding: 12px; text-align: left;">${{team.name}}</td>
                                        <td style="padding: 12px; text-align: right; color: var(--theme-pink); font-weight: 600;">${{team.score}}</td>
                                    </tr>
                                `;
                            }}).join('')}}
                        </tbody>
                    </table>
                `;
                
                tableContainer.innerHTML = tableHtml;
                
            }} catch (err) {{
                console.error('Errore caricamento classifica finale:', err);
                container.innerHTML = '<p style="color: #b91c1c;">Errore nel caricamento della classifica finale</p>';
                tableContainer.innerHTML = '<p style="color: #b91c1c;">Impossibile caricare i dati. Riprova più tardi.</p>';
            }}
        }}
        
        async function loadParticipants() {{
            try {{
                const filterNameEl = document.getElementById('filterName');
                if (filterNameEl) filterNameEl.value = '';

                const response = await fetch(`${{API_BASE}}/participants`);
                const payload = await response.json();
                if (!response.ok) {{
                    throw new Error(String(payload?.detail || 'Errore nel caricamento partecipanti'));
                }}
                allParticipants = Array.isArray(payload) ? payload : [];
                if (!Array.isArray(payload)) {{
                    console.warn('Risposta partecipanti non valida:', payload);
                    showStatus('status', 'Formato risposta partecipanti non valido.', 'error');
                }}
                // dopo il fetch mostra la vista di default per lo sport selezionato
                renderMarketBySport();
            }} catch (err) {{
                console.error('Errore caricamento partecipanti:', err);
                const list = document.getElementById('marketList');
                if (list) {{
                    list.innerHTML = '<div style="text-align:center; padding:20px; color:#b91c1c;">Errore nel caricamento dei partecipanti</div>';
                }}
                showStatus('status', `Impossibile caricare il mercato: ${{err.message || err}}`, 'error');
            }}
        }}

        // Render per-sport: mostra cards con nome partecipante, composed_of e bottone buy/sell
        function prepareMarketSportSelect(selectEl) {{
            if (!selectEl || !selectEl.options || !selectEl.options.length) return;
            if (selectEl.options[0].text === 'Seleziona Sport') {{
                selectEl.options[0].text = 'Tutti';
            }}
        }}

        function renderMarketBySport() {{
            const container = document.getElementById('marketList');
            if (!container) return;

            const sport = (document.getElementById('sportSelect')?.value || 'all').toLowerCase();
            const q = (document.getElementById('filterName')?.value || '').toLowerCase();

            const filtered = allParticipants.filter(p => {{
                const role = (p.role || p.sport || '').toString().toLowerCase();
                const matchSport = sport === 'all' ? true : (role === sport);
                const matchQuery = !q || (p.name || '').toString().toLowerCase().includes(q) || (p.composed_of || '').toString().toLowerCase().includes(q);
                return matchSport && matchQuery;
            }});

            if (!filtered.length) {{
                container.innerHTML = '<div style="text-align:center; padding:20px; color: rgba(238,243,251,0.72);">Nessun partecipante per lo sport selezionato</div>';
                return;
            }}

            const html = filtered.map(p => {{
                const owners = Array.isArray(p.owner_user_ids) ? p.owner_user_ids : (p.owner_user_ids || []);
                const owned = isOwnedByCurrentUser(p);
                const composed = (p.composed_of || '').toString().split(',').map(x => x.trim()).filter(x => x).join(' · ') || 'N/D';
                const cost = Number(p.cost || 0);
                const canBuy = Number(currentDomeBalance || 0) >= cost;
                const buttonHtml = owned
                    ? `<button class="btn btn-sell" onclick="sellParticipant(${{p.id}}, ${{cost}}, 'status')">Vendi</button>`
                    : (canBuy
                        ? `<button class="btn btn-buy" onclick="buyParticipant(${{p.id}}, ${{cost}}, 'status')">Acquista</button>`
                        : `<button class="btn btn-buy" disabled style="opacity:0.5; cursor:not-allowed;">Acquista</button>`);
                const hintHtml = (!owned && !canBuy)
                    ? `<div style="margin-top:8px; font-size:12px; color:#b91c1c;">Saldo insufficiente: servono ${{cost}} DomeCoin</div>`
                    : '';

                return `
                    <div class="market-card">
                        <div>
                            <div class="market-card-title">${{p.name || ('Partecipante ' + p.id)}}</div>
                            <div class="market-card-subtitle">Ruolo: ${{p.role || '-'}} · ${{p.sport || p.role || 'Sport N/D'}}</div>
                            <div class="market-composed">${{composed}}</div>
                        </div>
                        <div class="market-card-actions">
                            <div class="market-card-cost">${{cost}} DomeCoin</div>
                            <div>
                                ${{buttonHtml}}
                            </div>
                            ${{hintHtml}}
                        </div>
                    </div>
                `;
            }}).join('');

            container.innerHTML = html;
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
                const participantsResponse = await fetch(`${{API_BASE}}/participants`);
                const participantsPayload = participantsResponse.ok ? await participantsResponse.json() : [];
                const participantsMap = new Map(
                    (Array.isArray(participantsPayload) ? participantsPayload : []).map(p => [Number(p.id), p])
                );
                const teamsResponse = await fetch(`${{API_BASE}}/teams`);
                const teamsPayload = teamsResponse.ok ? await teamsResponse.json() : [];
                const teamRow = (Array.isArray(teamsPayload) ? teamsPayload : []).find(t => Number(t.id) === Number(teamId));
                const displayName = ((profile.name || '') + ' ' + (profile.surname || '')).trim();
                const userEmail = payload.email || profile.email || 'N/D';
                const teamName = (teamRow && teamRow.name)
                    ? teamRow.name
                    : (displayName ? `${{displayName}}'s team` : `Team ${{teamId}}`);
                const totalScore = Number(teamRow?.score ?? payload?.team_score ?? 0);
                const bonusItems = Array.isArray(payload?.bonus_items) ? payload.bonus_items : [];
                const bonusTotal = Number(payload?.bonus_total || 0);
                const listRows = roster.length
                    ? roster.map(item => {{
                        const participantId = Number(item.participant_id);
                        const participant = participantsMap.get(participantId) || {{}};
                        const squadraLabel = item.participant_name || participant.name || 'N/D';
                        const composedRaw = (participant.composed_of || '').toString();
                        const partecipantiLabel = composedRaw
                            ? composedRaw.split(',').map(v => v.trim()).filter(Boolean).join(', ')
                            : 'N/D';
                        return `
                            <tr>
                                <td>${{squadraLabel}}</td>
                                <td>${{partecipantiLabel}}</td>
                            </tr>
                        `;
                    }}).join('')
                    : '<tr><td colspan="2" style="opacity:0.8;">Nessun participant acquistato</td></tr>';

                let bonusRows = '';
                if (bonusItems.length) {{
                    bonusRows = bonusItems.map(item => `
                        <tr>
                            <td>${{item.name || 'Tipo N/D'}}</td>
                            <td>${{item.participant_name || 'Squadra N/D'}}</td>
                            <td>${{item.reason || 'Motivo non specificato'}}</td>
                            <td>${{item.points || 0}}</td>
                        </tr>
                    `).join('');
                }} else if (bonusTotal && Number(bonusTotal) > 0) {{
                    // Non ci sono voci dettagliate, ma esiste un totale bonus: mostralo come riga aggregata
                    bonusRows = `
                        <tr>
                            <td>Generico</td>
                            <td>—</td>
                            <td>Bonus applicato (aggregato)</td>
                            <td>${{bonusTotal}}</td>
                        </tr>
                    `;
                }} else {{
                    bonusRows = '<tr><td colspan="4" style="opacity:0.8;">Nessun bonus registrato</td></tr>';
                }}

                container.innerHTML = `
                    <h3>${{teamName}}</h3>
                    <p>Account: ${{userEmail}}</p>
                    <div style="margin-top: 8px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                        <button id="editTeamNameBtn" class="btn btn-buy-section" onclick="toggleTeamNameEditor()">Modifica nome</button>
                    </div>
                    <div id="teamNameEditor" style="display: none; margin-top: 10px; gap: 10px; align-items: center; flex-wrap: wrap;">
                        <input id="teamNameInput" type="text" value="${{teamName}}" placeholder="Nome team" style="flex: 1; min-width: 220px; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px;" />
                        <button class="btn btn-buy-section" onclick="updateTeamName()">Salva nome team</button>
                        <button class="btn btn-logout" onclick="cancelTeamNameEdit()">Annulla</button>
                    </div>
                    <div id="teamNameStatus" class="status" style="margin-top: 10px;"></div>
                    <div class="score-grid">
                        <div class="score-metric">
                            <span class="label">Punteggio team</span>
                            <div class="value">${{totalScore}}</div>
                        </div>
                        <div class="score-metric">
                            <span class="label">Bonus attivi</span>
                            <div class="value">${{bonusTotal}}</div>
                        </div>
                        <div class="score-metric">
                            <span class="label">Participant nel team</span>
                            <div class="value">${{roster.length}}</div>
                        </div>
                    </div>
                    <div class="my-score-list">
                        <h4 style="padding:12px; margin:0; font-size:15px;">Il mio team</h4>
                        <table>
                            <thead>
                                <tr>
                                    <th>Squadra</th>
                                    <th>Partecipanti</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${{listRows}}
                            </tbody>
                        </table>
                    </div>
                    <div class="my-score-list" style="margin-top:16px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Tipo Bonus</th>
                                    <th>Squadra</th>
                                    <th>Motivo</th>
                                    <th>Punti</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${{bonusRows}}
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

        // Aggiorna il nome del team dell'utente autenticato.
        async function updateTeamName() {{
            const input = document.getElementById('teamNameInput');
            if (!input) return;
            const newName = (input.value || '').trim();

            if (!newName) {{
                showStatus('teamNameStatus', 'Inserisci un nome valido.', 'error');
                return;
            }}
            if (!authToken || !currentTeamId) {{
                showStatus('teamNameStatus', 'Team non disponibile. Riprova dopo il refresh.', 'error');
                return;
            }}

            try {{
                const res = await fetch(`${{API_BASE}}/teams/${{currentTeamId}}/name`, {{
                    method: 'PATCH',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${{authToken}}`
                    }},
                    body: JSON.stringify({{ name: newName }})
                }});

                let payload = {{}};
                try {{
                    payload = await res.json();
                }} catch (err) {{
                    payload = {{}};
                }}

                if (res.ok) {{
                    showStatus('teamNameStatus', '✓ Nome team aggiornato', 'success');
                    loadMyScore();
                    return;
                }}

                const detail = payload?.detail || 'Errore aggiornamento nome team';
                showStatus('teamNameStatus', `✗ ${{detail}}`, 'error');
            }} catch (err) {{
                showStatus('teamNameStatus', `✗ Errore: ${{err.message || err}}`, 'error');
            }}
        }}

        function toggleTeamNameEditor() {{
            const editor = document.getElementById('teamNameEditor');
            if (!editor) return;
            editor.style.display = (editor.style.display === 'none' || !editor.style.display) ? 'flex' : 'none';
        }}

        function cancelTeamNameEdit() {{
            const editor = document.getElementById('teamNameEditor');
            const input = document.getElementById('teamNameInput');
            if (input) {{
                input.value = input.defaultValue || input.value;
            }}
            if (editor) editor.style.display = 'none';
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
            `).join('') : '<tr><td colspan="7" style="text-align: center; padding: 20px; color: rgba(238,243,251,0.72);">Nessun partecipante trovato</td></tr>';
            
            document.getElementById('participantsTable').innerHTML = html;
        }}
        
        async function buyParticipant(participantId, cost, statusTarget) {{
            if (!authToken) {{
                showStatus(statusTarget || 'status', 'Errore: token non trovato. Effettua login prima.', 'error');
                return;
            }}

            const numericCost = Number(cost || 0);
            if (Number(currentDomeBalance || 0) < numericCost) {{
                showStatus(statusTarget || 'status', `Operazione non possibile: saldo insufficiente. Hai ${{currentDomeBalance}} DomeCoin, ne servono ${{numericCost}}.`, 'error');
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
            applyFaseLogic(); // Applica visibilità tab in base alla fase
            await loadMyScore();
            await loadBalance();
            loadRanking();
            await loadFinalStandings();
            // Popola subito il mercato, perché la navigazione a tab non è più presente.
            await loadParticipants();
        }});

        // Carica e mostra il saldo DomeCoin dell'utente
        async function loadBalance() {{
            const el = document.getElementById('domeBalance');
            if (!el) return;
            if (!authToken) {{
                el.textContent = 'DomeCoin: —';
                currentDomeBalance = 0;
                renderMarketBySport();
                return;
            }}

            try {{
                const resp = await fetch(`${{API_BASE}}/users/me`, {{ headers: {{ 'Authorization': `Bearer ${{authToken}}` }} }});
                if (!resp.ok) {{
                    el.textContent = 'DomeCoin: —';
                    currentDomeBalance = 0;
                    showStatus('status', 'Impossibile leggere il saldo DomeCoin. Riprova dopo il login.', 'error');
                    renderMarketBySport();
                    return;
                }}
                const payload = await resp.json();
                const profile = payload?.profile || {{}};
                const raw = profile?.dome_balance ?? payload?.dome_balance ?? profile?.team_balance ?? payload?.team_balance ?? profile?.balance ?? payload?.balance ?? 0;
                const num = Number(raw) || 0;
                currentDomeBalance = num;
                const formatted = num.toLocaleString('it-IT', {{ minimumFractionDigits: 0, maximumFractionDigits: 2 }});
                el.textContent = `DomeCoin: ${{formatted}}`;
                renderMarketBySport();
            }} catch (err) {{
                console.warn('Impossibile caricare DomeCoin:', err);
                el.textContent = 'DomeCoin: —';
                currentDomeBalance = 0;
                showStatus('status', 'Errore nel recupero saldo DomeCoin.', 'error');
                renderMarketBySport();
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
                            <div class="modal-stat-value" style="color: ${{diffReti > 0 ? 'var(--theme-sky)' : diffReti < 0 ? 'var(--theme-pink)' : '#666'}};">${{diffReti > 0 ? '+' : ''}}${{diffReti}}</div>
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
        
        // Ascolta cambamenti di fase da altre tab
        window.addEventListener('storage', function(e) {{
            if (e.key === 'tournamentFase') {{
                applyFaseLogic();
            }}
        }});
    </script>
</body>
</html>
"""
    
    return HTMLResponse(content=html)
