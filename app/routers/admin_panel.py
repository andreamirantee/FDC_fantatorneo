"""Pannello amministrativo per gestione torneo.

Interfaccia HTML + endpoint per admin:
- Aggiungere/eliminare squadre (partecipanti = squadre)
- Inserire risultati partite con calcolo automatico punti
- Punti distribuiti automaticamente ai team owner
- Visualizzare elenco squadre e team

Protezione: richiede header X-Admin-Token valido.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from ..database import get_supabase_client

router = APIRouter(tags=["Admin"], include_in_schema=False)


def verify_admin_token(token: str = None) -> bool:
	"""Verifica token admin da header X-Admin-Token."""
	return token == "a3f9c4b8de"


@router.get("/admin", response_class=HTMLResponse)
def serve_admin_panel():
	"""Pagina HTML interattiva per amministratori torneo."""

	html = """
<!DOCTYPE html>
<html lang="it">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>Admin - FDC Fantatorneo</title>
	<style>
		* { margin: 0; padding: 0; box-sizing: border-box; }
		body {
			font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
			background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
			color: #e5e7eb;
			min-height: 100vh;
			padding: 20px;
		}
		.container { max-width: 1800px; margin: 0 auto; }
		.header {
			background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
			color: white;
			padding: 30px;
			border-radius: 12px;
			margin-bottom: 30px;
			display: flex;
			justify-content: space-between;
			align-items: center;
		}
		.header h1 { font-size: 2em; }
		.auth-section { background: rgba(0,0,0,0.3); padding: 15px 20px; border-radius: 8px; display: flex; gap: 10px; align-items: center; }
		.auth-section input { padding: 8px 12px; border: 1px solid #4b5563; background: #1f2937; color: white; border-radius: 4px; }
		.auth-section button { padding: 8px 16px; background: #10b981; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; }
		.auth-section button:hover { background: #059669; }
		.auth-status { padding: 8px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; display: none; }
		.auth-status.success { background: #d1fae5; color: #065f46; display: block; }
		.auth-status.error { background: #fee2e2; color: #991b1b; display: block; }

		.content { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
		.panel { background: #1f2937; border: 1px solid #374151; border-radius: 12px; padding: 25px; }
		.panel h2 { color: #7c3aed; margin-bottom: 20px; font-size: 1.5em; }
		.form-group { margin-bottom: 15px; display: flex; flex-direction: column; }
		.form-group label { font-size: 13px; font-weight: 600; color: #9ca3af; margin-bottom: 5px; }
		.form-group input, .form-group select { padding: 10px 12px; border: 1px solid #374151; background: #111827; color: #e5e7eb; border-radius: 6px; font-size: 13px; }
		.btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; width: 100%; }
		.btn-primary { background: #7c3aed; color: white; }
		.btn-primary:hover { background: #6d28d9; }
		.btn-danger { background: #ef4444; color: white; }
		.btn-danger:hover { background: #dc2626; }
		.status { margin-top: 15px; padding: 12px; border-radius: 6px; font-size: 13px; display: none; }
		.status.success { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid #10b981; display: block; }
		.status.error { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid #ef4444; display: block; }

		table { width: 100%; border-collapse: collapse; margin-top: 15px; }
		thead { background: rgba(124, 58, 237, 0.1); }
		th { padding: 12px; text-align: left; font-weight: 600; font-size: 12px; color: #7c3aed; text-transform: uppercase; border-bottom: 1px solid #374151; }
		td { padding: 12px; border-bottom: 1px solid #374151; font-size: 13px; }
		tr:hover { background: rgba(124, 58, 237, 0.05); }

		.admin-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
		.admin-table th { background: rgba(124, 58, 237, 0.2); }
		.admin-table input {
			width: 100%;
			padding: 6px 8px;
			border: 1px solid #374151;
			background: #0f172a;
			color: #e5e7eb;
			border-radius: 6px;
			font-size: 12px;
		}
		.admin-table input:focus { outline: none; border-color: #7c3aed; }
		.btn-save {
			background: #10b981;
			color: white;
			border: none;
			border-radius: 6px;
			padding: 6px 12px;
			font-size: 12px;
			font-weight: 600;
			cursor: pointer;
		}
		.btn-save:hover { background: #059669; }

		.full-width { grid-column: 1 / -1; }
		.section-block { margin-bottom: 24px; }
		.section-title {
			font-size: 20px;
			font-weight: 700;
			margin-bottom: 12px;
			color: #c4b5fd;
			border-left: 4px solid #7c3aed;
			padding-left: 10px;
		}
		.section-hint {
			font-size: 13px;
			color: #9ca3af;
			margin-bottom: 14px;
		}
		.card-grid {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
			gap: 16px;
		}
		.logic-box {
			margin-top: 10px;
			padding: 10px 12px;
			border-radius: 8px;
			background: rgba(59, 130, 246, 0.15);
			border: 1px solid rgba(96, 165, 250, 0.4);
			font-size: 12px;
			line-height: 1.45;
			color: #bfdbfe;
		}
		.bonus-placeholder {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
			gap: 10px;
		}
		.bonus-placeholder button {
			padding: 10px;
			border-radius: 8px;
			border: 1px dashed #6b7280;
			background: #111827;
			color: #9ca3af;
			cursor: not-allowed;
		}
		@media (max-width: 1200px) {
			.content { grid-template-columns: 1fr; }
		}
		@media (max-width: 768px) {
			body { padding: 12px; }
			.header { padding: 18px; flex-direction: column; align-items: flex-start; gap: 12px; }
			.auth-section { width: 100%; flex-wrap: wrap; }
			.auth-section input, .auth-section button { width: 100%; }
			.panel { padding: 16px; }
			th, td { padding: 8px; font-size: 12px; }
		}
	</style>
</head>
<body>
	<div class="container">
		<div class="header">
			<div>
				<h1>⚙️ Admin Panel - FDC Fantatorneo</h1>
				<p>Gestione squadre, partite, punti automatici</p>
			</div>
			<div class="auth-section">
				<label style="color: white; font-size: 12px;">Token:</label>
				<input type="password" id="adminToken" />
				<button onclick="authenticateAdmin()">Accedi</button>
				<div id="authStatus" class="auth-status"></div>
			</div>
		</div>

		<div id="adminContent" style="display: none;">
			<div class="section-block">
				<div class="section-title">Squadre</div>
				<div class="section-hint">Gestione completa squadre: aggiungi, modifica, elimina.</div>
				<div class="card-grid">
					<div class="panel">
						<h2>➕ Aggiungi Squadra</h2>
						<form onsubmit="addSquad(event)">
							<div class="form-group">
								<label>Nome Squadra</label>
								<input type="text" id="squadName" required>
							</div>
							<div class="form-group">
								<label>Sport</label>
								<select id="squadSport" required onchange="updateCost()">
									<option value="">Seleziona sport</option>
									<option value="Calcio">Calcio (35 DomeCoin)</option>
									<option value="Pallavolo">Pallavolo (25 DomeCoin)</option>
									<option value="Padel">Padel (20 DomeCoin)</option>
								</select>
							</div>
							<div class="form-group">
								<label>Costo (auto)</label>
								<input type="number" id="squadCost" readonly>
							</div>
							<div class="form-group">
								<label>Composto da</label>
								<input type="text" id="squadComposedOf" placeholder="Nomi separati da virgola...">
							</div>
							<button type="submit" class="btn btn-primary">Crea Squadra</button>
							<div id="addSquadStatus" class="status"></div>
						</form>
					</div>

					<div class="panel">
						<h2>✏️ Modifica Squadra</h2>
						<form onsubmit="updateSquad(event)">
							<div class="form-group">
								<label>Squadra</label>
								<select id="editSquadSelect" required>
									<option value="">Seleziona squadra</option>
								</select>
							</div>
							<div class="form-group">
								<label>Nuovo nome</label>
								<input type="text" id="editSquadName" required>
							</div>
							<div class="form-group">
								<label>Sport</label>
								<select id="editSquadSport" required>
									<option value="Calcio">Calcio</option>
									<option value="Pallavolo">Pallavolo</option>
									<option value="Padel">Padel</option>
								</select>
							</div>
							<div class="form-group">
								<label>Costo</label>
								<input type="number" id="editSquadCost" min="0" required>
							</div>
							<div class="form-group">
								<label>Partecipanti squadra (composed_of)</label>
								<input type="text" id="editSquadComposedOf" placeholder="Nomi separati da virgola...">
							</div>
							<button type="submit" class="btn btn-primary">Salva Modifiche</button>
							<div id="editSquadStatus" class="status"></div>
						</form>
					</div>

					<div class="panel">
						<h2>🗑️ Elimina Squadra</h2>
						<form onsubmit="deleteSquadHandler(event)">
							<div class="form-group">
								<label>Squadra</label>
								<select id="deleteSquadSelect" required>
									<option value="">Seleziona squadra</option>
								</select>
							</div>
							<p style="font-size: 12px; color: #f87171; margin-bottom: 15px;">⚠️ Azione irreversibile.</p>
							<button type="submit" class="btn btn-danger">Elimina</button>
							<div id="deleteStatus" class="status"></div>
						</form>
					</div>
				</div>
			</div>

			<div class="section-block">
				<div class="section-title">Classifica</div>
				<div class="section-hint">Visualizza e modifica classifica per team utenti o sport.</div>
				<div class="panel full-width">
					<h2>📋 Visualizza Classifica</h2>
					<div style="display: flex; gap: 12px; align-items: center; margin-bottom: 20px;">
						<label for="classifyViewSelect" style="font-weight: 600; color: #e5e7eb;">Seleziona vista:</label>
						<select id="classifyViewSelect" onchange="loadRankingView()" style="padding: 8px 12px; background: #111827; color: #e5e7eb; border: 1px solid #374151; border-radius: 6px;">
							<option value="teams">👥 Team Utenti</option>
							<option value="calcio">⚽ Calcio</option>
							<option value="pallavolo">🏐 Pallavolo</option>
							<option value="padel">🎾 Padel</option>
						</select>
					</div>
					<div style="overflow-x: auto;" id="rankingViewContainer">
						<p style="text-align: center; color: #9ca3af;">Caricamento classifica...</p>
					</div>
				</div>
				<div class="panel full-width">
					<h2>✏️ Modifica Classifica</h2>
					<p style="color: #9ca3af; font-size: 13px; margin-bottom: 15px;">Aggiorna PF, V, S, GF/GS o SV/SP e punteggi.</p>
					<div style="margin-bottom: 20px;">
						<h3 style="margin-bottom: 10px;">🏆 Partecipanti (Squadre)</h3>
						<div id="adminParticipantsContainer">Caricamento...</div>
					</div>
					<div>
						<h3 style="margin-bottom: 10px;">👥 Team Gestori</h3>
						<div id="adminTeamsContainer">Caricamento...</div>
					</div>
				</div>
			</div>

			<div class="section-block">
				<div class="section-title">Partita</div>
				<div class="section-hint">Aggiungi, modifica o elimina partite con logica punteggio guidata per sport.</div>
				<div class="card-grid">
					<div class="panel">
						<h2>🏟️ Aggiungi Partita</h2>
						<form onsubmit="recordMatch(event)">
							<div class="form-group">
								<label>Sport partita</label>
								<select id="matchSport" required onchange="updateMatchLogicPreview()">
									<option value="Calcio">Calcio</option>
									<option value="Pallavolo">Pallavolo</option>
									<option value="Padel">Padel</option>
								</select>
							</div>
							<div class="form-group">
								<label>Squadra A</label>
								<select id="homeSquad" required><option value="">Seleziona squadra</option></select>
							</div>
							<div class="form-group">
								<label>Squadra B</label>
								<select id="awaySquad" required><option value="">Seleziona squadra</option></select>
							</div>
							<div class="form-group">
								<label>Fase</label>
								<select id="matchStage" required>
									<option value="group">Girone</option>
									<option value="final">Finale</option>
								</select>
							</div>
							<div class="form-group">
								<label>Gol/Set A</label>
								<input type="number" id="homeScore" min="0" required oninput="updateMatchLogicPreview()">
							</div>
							<div class="form-group">
								<label>Gol/Set B</label>
								<input type="number" id="awayScore" min="0" required oninput="updateMatchLogicPreview()">
							</div>
							<div id="matchLogicPreview" class="logic-box"></div>
							<button type="submit" class="btn btn-primary">Registra Partita</button>
							<div id="matchStatus" class="status"></div>
						</form>
					</div>

					<div class="panel">
						<h2>✏️ Modifica Partita</h2>
						<form onsubmit="updateMatch(event)">
							<div class="form-group">
								<label>Partita</label>
								<select id="editMatchSelect" required><option value="">Seleziona partita</option></select>
							</div>
							<div class="form-group">
								<label>Sport</label>
								<select id="editMatchSport">
									<option value="calcio">Calcio</option>
									<option value="pallavolo">Pallavolo</option>
									<option value="padel">Padel</option>
								</select>
							</div>
							<div class="form-group">
								<label>Gol/Set A</label>
								<input type="number" id="editHomeScore" min="0" required>
							</div>
							<div class="form-group">
								<label>Gol/Set B</label>
								<input type="number" id="editAwayScore" min="0" required>
							</div>
							<button type="submit" class="btn btn-primary">Salva Partita</button>
							<div id="editMatchStatus" class="status"></div>
						</form>
					</div>

					<div class="panel">
						<h2>🗑️ Elimina Partita</h2>
						<form onsubmit="deleteMatch(event)">
							<div class="form-group">
								<label>Partita</label>
								<select id="deleteMatchSelect" required><option value="">Seleziona partita</option></select>
							</div>
							<button type="submit" class="btn btn-danger">Elimina Partita</button>
							<div id="deleteMatchStatus" class="status"></div>
						</form>
					</div>
				</div>
				<div class="panel full-width" style="margin-top:16px;">
					<h2>🏐 Pallavolo - Gironi e Finali</h2>
					<div id="volleyStructureContainer">Caricamento...</div>
				</div>
			</div>

			<div class="section-block">
				<div class="section-title">Bonus</div>
				<div class="section-hint">Sezione progettuale bonus. Tipologie in definizione.</div>
				<div class="panel">
					<div class="bonus-placeholder">
						<button disabled>Bonus Fair Play</button>
						<button disabled>Bonus Vittoria</button>
						<button disabled>Bonus Clean Sheet</button>
						<button disabled>Bonus Rimonta</button>
						<button disabled>Bonus Goal Difference</button>
						<button disabled>Bonus MVP</button>
					</div>
				</div>
			</div>
		</div>
	</div>

	<script>
		const API_BASE = '/api/v1';
		const ADMIN_TOKEN_STORAGE_KEY = 'fdc_admin_token';
		let adminToken = null;
		let lastSquads = [];
		let lastMatches = [];
		const sportCosts = { 'Calcio': 35, 'Pallavolo': 25, 'Padel': 20 };

		function getAdminToken() {
			return adminToken || localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
		}

		function saveAdminToken(token) {
			adminToken = token;
			localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, token);
		}

		function initAdminToken() {
			const storedToken = localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
			if (storedToken) {
				adminToken = storedToken;
				const tokenInput = document.getElementById('adminToken');
				tokenInput.value = storedToken;
				tokenInput.disabled = true;
				document.getElementById('adminContent').style.display = 'block';
				showAuthStatus('✓ Token admin caricato', 'success');
				loadSquads();
				loadAdminData();
				loadMatches();
				loadVolleyStructure();
				updateMatchLogicPreview();
			}
		}

		function authenticateAdmin() {
			const tokenValue = document.getElementById('adminToken').value;
			if (!tokenValue) {
				showAuthStatus('Inserisci token', 'error');
				return;
			}

			if (tokenValue === 'a3f9c4b8de') {
				saveAdminToken(tokenValue);
				showAuthStatus('✓ Autenticazione riuscita', 'success');
				document.getElementById('adminContent').style.display = 'block';
				document.getElementById('adminToken').disabled = true;
				loadSquads();
				loadAdminData();
				loadMatches();
				loadVolleyStructure();
				updateMatchLogicPreview();
			} else {
				showAuthStatus('✗ Token non valido', 'error');
			}
		}

		function showAuthStatus(msg, type) {
			const el = document.getElementById('authStatus');
			el.textContent = msg;
			el.className = 'auth-status ' + type;
		}

		function showStatus(id, msg, type) {
			const el = document.getElementById(id);
			el.textContent = msg;
			el.className = 'status ' + type;
		}

		async function readResponseMessage(response) {
			const contentType = response.headers.get('content-type') || '';
			if (contentType.includes('application/json')) {
				try {
					const payload = await response.json();
					return payload.detail || payload.message || JSON.stringify(payload);
				} catch (error) {
					return 'Errore non valido';
				}
			}

			try {
				const text = await response.text();
				return text || 'Errore non valido';
			} catch (error) {
				return 'Errore non valido';
			}
		}

		function updateCost() {
			const sport = document.getElementById('squadSport').value;
			const cost = sportCosts[sport] || 0;
			document.getElementById('squadCost').value = cost;
		}

		function computeAwardedPoints(sportKey, homeScore, awayScore) {
			const sport = String(sportKey || '').toLowerCase();
			if (sport === 'calcio') {
				if (homeScore > awayScore) return { home: 3, away: 0 };
				if (awayScore > homeScore) return { home: 0, away: 3 };
				return { home: 1, away: 1 };
			}
			if (sport === 'pallavolo') {
				if (homeScore > awayScore) return { home: 3, away: 1 };
				if (awayScore > homeScore) return { home: 1, away: 3 };
				return { home: 2, away: 2 };
			}
			if (homeScore > awayScore) return { home: 1, away: 0 };
			if (awayScore > homeScore) return { home: 0, away: 1 };
			return { home: 1, away: 1 };
		}

		function updateMatchLogicPreview() {
			const el = document.getElementById('matchLogicPreview');
			if (!el) return;
			const sport = document.getElementById('matchSport')?.value || 'Calcio';
			const home = parseInt(document.getElementById('homeScore')?.value || '0') || 0;
			const away = parseInt(document.getElementById('awayScore')?.value || '0') || 0;
			const p = computeAwardedPoints(sport, home, away);
			const metricWin = sport === 'Pallavolo' || sport === 'Padel' ? 'set vinti' : 'gol fatti';
			const metricLose = sport === 'Pallavolo' || sport === 'Padel' ? 'set persi' : 'gol subiti';
			el.innerHTML = `Logica ${sport}: A ${home}-${away} B → A ${p.home} punti, ${home} ${metricWin}, ${away} ${metricLose}; B ${p.away} punti, ${away} ${metricWin}, ${home} ${metricLose}.`;
		}

		async function loadAdminData() {
			try {
				const [rankingRes, teamsRes] = await Promise.all([
					fetch(`${API_BASE}/market/ranking`),
					fetch(`${API_BASE}/teams`)
				]);

				const ranking = rankingRes.ok ? await rankingRes.json() : [];
				const teams = teamsRes.ok ? await teamsRes.json() : [];

				renderAdminParticipantsTable(ranking);
				renderAdminTeamsTable(teams);
			} catch (err) {
				console.error('Errore caricamento admin:', err);
				document.getElementById('adminParticipantsContainer').innerHTML = '<p style="color: #fca5a5;">Errore caricamento</p>';
				document.getElementById('adminTeamsContainer').innerHTML = '<p style="color: #fca5a5;">Errore caricamento</p>';
			}
		}

		async function loadVolleyStructure() {
			const container = document.getElementById('volleyStructureContainer');
			if (!container) return;
			try {
				const response = await fetch(`${API_BASE}/market/volley/structure`);
				const payload = response.ok ? await response.json() : null;
				if (!response.ok || !payload) {
					container.innerHTML = '<p style="color: #fca5a5;">Errore caricamento</p>';
					return;
				}
				container.innerHTML = renderVolleyStructure(payload);
			} catch (err) {
				container.innerHTML = '<p style="color: #fca5a5;">Errore caricamento</p>';
			}
		}

		function renderVolleyStructure(data) {
			const groupA = (data.groups && data.groups.A) || [];
			const groupB = (data.groups && data.groups.B) || [];
			const finals = data.finals || {};

			const renderGroupTable = (title, teams) => {
				const rows = teams.length
					? teams.map((team, index) => `
						<tr>
							<td>${index + 1}</td>
							<td>${team.name || 'Squadra ' + team.id}</td>
							<td>${team.matches_played || 0}</td>
							<td>${team.wins || 0}</td>
							<td>${team.losses || 0}</td>
							<td>${team.sets_won || 0}</td>
							<td>${team.sets_lost || 0}</td>
							<td>${team.points || 0}</td>
						</tr>
					`).join('')
					: '<tr><td colspan="8" style="text-align:center; color:#9ca3af;">Nessuna squadra</td></tr>';
				return `
					<h3 style="margin: 10px 0;">${title}</h3>
					<table class="admin-table">
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
							${rows}
						</tbody>
					</table>
				`;
			};

			const formatTeamName = (team) => team ? (team.name || ('Squadra ' + team.id)) : '-';
			const formatScore = (pair) => {
				if (!pair || !pair.match || !pair.home || !pair.away) return '-';
				const match = pair.match;
				const homeScore = match.home_score ?? 0;
				const awayScore = match.away_score ?? 0;
				return match.home_squad_id === pair.home.id
					? `${homeScore}-${awayScore}`
					: `${awayScore}-${homeScore}`;
			};

			const renderFinalRow = (label, pair) => `
				<tr>
					<td>${label}</td>
					<td>${formatTeamName(pair.home)}</td>
					<td>${formatTeamName(pair.away)}</td>
					<td>${formatScore(pair)}</td>
				</tr>
			`;

			return `
				${renderGroupTable('Girone A', groupA)}
				${renderGroupTable('Girone B', groupB)}
				<h3 style="margin: 20px 0 10px;">Finali</h3>
				<table class="admin-table">
					<thead>
						<tr>
							<th>Fase</th>
							<th>Squadra</th>
							<th>Squadra</th>
							<th>Risultato</th>
						</tr>
					</thead>
					<tbody>
						${renderFinalRow('Finale 5/6', finals.fifth_sixth || {})}
						${renderFinalRow('Finale 3/4', finals.third_fourth || {})}
						${renderFinalRow('Finale 1/2', finals.final || {})}
					</tbody>
				</table>
			`;
		}

		function renderAdminParticipantsTable(participants) {
			const isCalcio = (item) => (item.sport || item.role || '').toLowerCase() === 'calcio';
			let html = `
				<table class="admin-table">
					<thead>
						<tr>
							<th>ID</th>
							<th>Nome</th>
							<th>Sport</th>
							<th>Gir</th>
							<th>PF</th>
							<th>V</th>
							<th>S</th>
							<th>GF/SV</th>
							<th>GS/SP</th>
							<th>Pti</th>
							<th>Azione</th>
						</tr>
					</thead>
					<tbody>
			`;

			participants.forEach(p => {
				const sport = p.sport || p.role || 'N/A';
				const isCal = sport.toLowerCase() === 'calcio';
				const isVolley = sport.toLowerCase() === 'pallavolo';
				const gf = isCal ? (p.goals_for || 0) : (p.sets_won || 0);
				const gs = isCal ? (p.goals_against || 0) : (p.sets_lost || 0);
				const groupValue = (p.group_code || '').toUpperCase();
				const groupCell = isVolley
					? `<select id="group_${p.id}">
						<option value="" ${groupValue === '' ? 'selected' : ''}></option>
						<option value="A" ${groupValue === 'A' ? 'selected' : ''}>A</option>
						<option value="B" ${groupValue === 'B' ? 'selected' : ''}>B</option>
					</select>`
					: '<span>-</span>';
				const composedOfDisplay = (p.composed_of || '').substring(0, 30) + ((p.composed_of && p.composed_of.length > 30) ? '...' : '');
				html += `
					<tr>
						<td>${p.id}</td>
						<td>${p.name || 'N/A'}</td>
						<td>${sport}</td>
						<td>${groupCell}</td>
						<td><input type="number" value="${p.matches_played || 0}" id="pg_${p.id}" min="0"></td>
						<td><input type="number" value="${p.wins || 0}" id="wins_${p.id}" min="0"></td>
						<td><input type="number" value="${p.losses || 0}" id="losses_${p.id}" min="0"></td>
						<td><input type="number" value="${gf}" id="gf_${p.id}" min="0"></td>
						<td><input type="number" value="${gs}" id="gs_${p.id}" min="0"></td>
						<td><input type="number" value="${p.points || p.score || 0}" id="points_${p.id}" min="0"></td>
						<td><input type="text" value="${(p.composed_of || '').replace(/"/g, '&quot;')}" id="composed_${p.id}" placeholder="Es: Ronaldo, Messi..."></td>
						<td><button class="btn-save" onclick="saveParticipantChanges(${p.id}, '${sport}')">Salva</button></td>
					</tr>
				`;
			});

			html += `</tbody></table>`;
			document.getElementById('adminParticipantsContainer').innerHTML = html;
		}

		function renderAdminTeamsTable(teams) {
			let html = `
				<table class="admin-table">
					<thead>
						<tr>
							<th>ID</th>
							<th>Nome Team</th>
							<th>Punteggio</th>
							<th>Crediti</th>
							<th>Azione</th>
						</tr>
					</thead>
					<tbody>
			`;

			teams.forEach(t => {
				html += `
					<tr>
						<td>${t.id}</td>
						<td>${t.name || 'Team ' + t.id}</td>
						<td><input type="number" value="${t.score || 0}" id="team_score_${t.id}" min="0"></td>
						<td><input type="number" value="${t.balance_credits || 0}" id="team_credits_${t.id}" min="0"></td>
						<td><button class="btn-save" onclick="saveTeamChanges(${t.id})">Salva</button></td>
					</tr>
				`;
			});

			html += `</tbody></table>`;
			document.getElementById('adminTeamsContainer').innerHTML = html;
		}

		async function loadRankingView() {
			const view = document.getElementById('classifyViewSelect')?.value || 'teams';
			const container = document.getElementById('rankingViewContainer');
			if (!container) return;

			try {
				if (view === 'teams') {
					// Mostra team utenti
					const teamsRes = await fetch(`${API_BASE}/teams`);
					const teams = teamsRes.ok ? await teamsRes.json() : [];
					const html = `
						<table class="admin-table" style="width: 100%;">
							<thead>
								<tr>
									<th>Pos</th>
									<th>Nome Team</th>
									<th>Punteggio</th>
									<th>Costo Totale</th>
									<th>Crediti Disponibili</th>
								</tr>
							</thead>
							<tbody>
								${teams.length ? teams.map((t, i) => `
									<tr>
										<td>${i + 1}</td>
										<td>${t.name || 'Team ' + t.id}</td>
										<td>${t.score || 0}</td>
										<td>${t.total_cost || 0}</td>
										<td>${t.balance_credits || 0}</td>
									</tr>
								`).join('') : '<tr><td colspan="5" style="text-align:center; color:#9ca3af;">Nessun team</td></tr>'}
							</tbody>
						</table>
					`;
					container.innerHTML = html;
				} else {
					// Mostra classifica sport
					const rankingRes = await fetch(`${API_BASE}/market/ranking`);
					const ranking = rankingRes.ok ? await rankingRes.json() : [];
					const sport = view.charAt(0).toUpperCase() + view.slice(1);
					const sportRanking = ranking.filter(item => {
						const role = (String(item.sport || item.role || '').toLowerCase());
						return role === view.toLowerCase();
					});

					const isCalcio = view === 'calcio';
					const html = `
						<table class="admin-table" style="width: 100%;">
							<thead>
								<tr>
									<th>Pos</th>
									<th>Squadra</th>
									<th>PF</th>
									<th>V</th>
									<th>S</th>
									<th>${isCalcio ? 'GF' : 'SV'}</th>
									<th>${isCalcio ? 'GS' : 'SP'}</th>
									${isCalcio ? '<th>DR</th>' : ''}
									<th>Pti</th>
								</tr>
							</thead>
							<tbody>
								${sportRanking.length ? sportRanking.map((team, i) => `
									<tr>
										<td>${i + 1}</td>
										<td>${team.name || 'Squadra ' + team.id}</td>
										<td>${team.matches_played || 0}</td>
										<td>${team.wins || 0}</td>
										<td>${team.losses || 0}</td>
										<td>${isCalcio ? (team.goals_for || 0) : (team.sets_won || 0)}</td>
										<td>${isCalcio ? (team.goals_against || 0) : (team.sets_lost || 0)}</td>
										${isCalcio ? `<td>${(team.goals_for || 0) - (team.goals_against || 0)}</td>` : ''}
										<td>${team.points ?? team.score ?? 0}</td>
									</tr>
								`).join('') : `<tr><td colspan="${isCalcio ? 9 : 8}" style="text-align:center; color:#9ca3af;">Nessuna squadra</td></tr>`}
							</tbody>
						</table>
					`;
					container.innerHTML = html;
				}
			} catch (err) {
				console.error('Errore caricamento ranking:', err);
				container.innerHTML = '<p style="color: #fca5a5;">Errore caricamento classifica</p>';
			}
		}

		async function saveParticipantChanges(participantId, sport) {
			const token = getAdminToken();
			if (!token) {
				alert('✗ Admin token required');
				return;
			}

			const pg = parseInt(document.getElementById(`pg_${participantId}`).value) || 0;
			const wins = parseInt(document.getElementById(`wins_${participantId}`).value) || 0;
			const losses = parseInt(document.getElementById(`losses_${participantId}`).value) || 0;
			const gf = parseInt(document.getElementById(`gf_${participantId}`).value) || 0;
			const gs = parseInt(document.getElementById(`gs_${participantId}`).value) || 0;
			const points = parseInt(document.getElementById(`points_${participantId}`).value) || 0;
			const composedOf = document.getElementById(`composed_${participantId}`).value || null;

			const isCal = sport.toLowerCase() === 'calcio';
			const isVolley = sport.toLowerCase() === 'pallavolo';
			const payload = {
				score: points,
				wins: wins,
				losses: losses,
				composed_of: composedOf
			};

			if (isVolley) {
				const groupEl = document.getElementById(`group_${participantId}`);
				payload.group_code = groupEl ? groupEl.value : '';
			}

			if (isCal) {
				payload.matches_played = pg;
				payload.goals_for = gf;
				payload.goals_against = gs;
			} else if (sport.toLowerCase() !== 'pallavolo') {
				payload.matches_played = pg;
				payload.sets_won = gf;
				payload.sets_lost = gs;
			}

			try {
				const response = await fetch(`${API_BASE}/market/admin/participants/${participantId}`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						'X-Admin-Token': token
					},
					body: JSON.stringify(payload)
				});

				if (response.ok) {
					alert(`✓ Partecipante ${participantId} aggiornato`);
				} else {
					const err = await response.json();
					alert(`✗ Errore: ${err.detail || 'Aggiornamento fallito'}`);
				}
			} catch (err) {
				alert(`✗ Errore: ${err.message}`);
			}
		}

		async function saveTeamChanges(teamId) {
			const token = getAdminToken();
			if (!token) {
				alert('✗ Admin token required');
				return;
			}

			const score = parseInt(document.getElementById(`team_score_${teamId}`).value) || 0;
			const credits = parseInt(document.getElementById(`team_credits_${teamId}`).value) || 0;

			try {
				const response = await fetch(`${API_BASE}/market/admin/teams/${teamId}`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						'X-Admin-Token': token
					},
					body: JSON.stringify({
						score: score,
						balance_credits: credits
					})
				});

				if (response.ok) {
					alert(`✓ Team ${teamId} aggiornato`);
				} else {
					const err = await response.json();
					alert(`✗ Errore: ${err.detail || 'Aggiornamento fallito'}`);
				}
			} catch (err) {
				alert(`✗ Errore: ${err.message}`);
			}
		}

		async function updateSquad(e) {
			e.preventDefault();
			const token = getAdminToken();
			if (!token) {
				showStatus('editSquadStatus', '✗ Admin token required', 'error');
				return;
			}

			const squadId = parseInt(document.getElementById('editSquadSelect').value);
			const payload = {
				name: document.getElementById('editSquadName').value,
				role: document.getElementById('editSquadSport').value,
				cost: parseInt(document.getElementById('editSquadCost').value || '0'),
				composed_of: document.getElementById('editSquadComposedOf').value || null,
			};

			try {
				const res = await fetch(`${API_BASE}/market/admin/participants/${squadId}`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
					body: JSON.stringify(payload)
				});

				if (res.ok) {
					showStatus('editSquadStatus', '✓ Squadra modificata', 'success');
					loadSquads();
					loadAdminData();
				} else {
					showStatus('editSquadStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('editSquadStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function addSquad(e) {
			e.preventDefault();

			const token = getAdminToken();
			if (!token) {
				showStatus('addSquadStatus', '✗ Admin token required', 'error');
				return;
			}

			const payload = {
				name: document.getElementById('squadName').value,
				role: document.getElementById('squadSport').value,
				cost: parseInt(document.getElementById('squadCost').value),
				composed_of: document.getElementById('squadComposedOf').value || null
			};

			try {
				const res = await fetch(`${API_BASE}/participants`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
					body: JSON.stringify(payload)
				});

				if (res.ok) {
					showStatus('addSquadStatus', '✓ Squadra creata', 'success');
					e.target.reset();
					window.location.reload();
				} else {
					showStatus('addSquadStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('addSquadStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function recordMatch(e) {
			e.preventDefault();

			const token = getAdminToken();
			if (!token) {
				showStatus('matchStatus', '✗ Admin token required', 'error');
				return;
			}

			const homeId = parseInt(document.getElementById('homeSquad').value);
			const awayId = parseInt(document.getElementById('awaySquad').value);
			const stage = document.getElementById('matchStage').value || 'group';

			if (homeId === awayId) {
				showStatus('matchStatus', '✗ Seleziona squadre diverse', 'error');
				return;
			}

			try {
				const res = await fetch(`${API_BASE}/market/match`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
					body: JSON.stringify({
						home_squad_id: homeId,
						away_squad_id: awayId,
						home_score: parseInt(document.getElementById('homeScore').value),
						away_score: parseInt(document.getElementById('awayScore').value),
						sport: document.getElementById('matchSport').value,
						stage: stage
					})
				});

				if (res.ok) {
					const data = await res.json();
					const sport = document.getElementById('matchSport').value;
					const metricWin = sport === 'Pallavolo' || sport === 'Padel' ? 'set vinti' : 'gol fatti';
					const metricLose = sport === 'Pallavolo' || sport === 'Padel' ? 'set persi' : 'gol subiti';
					const confirmMsg = `✓ Conferma: A ${data.home_points_awarded} punti (${document.getElementById('homeScore').value} ${metricWin}, ${document.getElementById('awayScore').value} ${metricLose}) | B ${data.away_points_awarded} punti (${document.getElementById('awayScore').value} ${metricWin}, ${document.getElementById('homeScore').value} ${metricLose})`;
					showStatus('matchStatus', confirmMsg, 'success');
					e.target.reset();
					updateMatchLogicPreview();
					loadMatches();
					loadAdminData();
				} else {
					showStatus('matchStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('matchStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function deleteSquadHandler(e) {
			e.preventDefault();

			const token = getAdminToken();
			if (!token) {
				showStatus('deleteStatus', '✗ Admin token required', 'error');
				return;
			}

			const squadId = document.getElementById('deleteSquadSelect').value;
			try {
				await fetch(`${API_BASE}/participants/${squadId}`, {
					method: 'DELETE',
					headers: { 'X-Admin-Token': token }
				});
				window.location.reload();
			} catch (err) {
				showStatus('deleteStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function assignPoints(e) {
			e.preventDefault();

			const token = getAdminToken();
			if (!token) {
				showStatus('pointsStatus', '✗ Admin token required', 'error');
				return;
			}

			const squadId = parseInt(document.getElementById('pointsSquad').value);
			const points = parseInt(document.getElementById('pointsAmount').value);

			try {
				const res = await fetch(`${API_BASE}/participants/${squadId}/points`, {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
					body: JSON.stringify({ points: points })
				});

				if (res.ok) {
					showStatus('pointsStatus', '✓ Punti assegnati', 'success');
					e.target.reset();
					window.location.reload();
				} else {
					showStatus('pointsStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('pointsStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function removePoints(e) {
			e.preventDefault();

			const token = getAdminToken();
			if (!token) {
				showStatus('removePointsStatus', '✗ Admin token required', 'error');
				return;
			}

			const squadId = parseInt(document.getElementById('removePointsSquad').value);
			const pointsToRemove = parseInt(document.getElementById('removePointsAmount').value);
			const selectedSquad = lastSquads.find(s => Number(s.id) === squadId);

			if (!selectedSquad) {
				showStatus('removePointsStatus', '✗ Seleziona una squadra valida', 'error');
				return;
			}

			const currentScore = parseInt(selectedSquad.score || 0);
			const newScore = Math.max(0, currentScore - pointsToRemove);
			const confirmed = window.confirm(`Rimuovere ${pointsToRemove} punti da ${selectedSquad.name}? Punteggio attuale: ${currentScore}, nuovo punteggio: ${newScore}`);
			if (!confirmed) {
				showStatus('removePointsStatus', 'Operazione annullata', 'error');
				return;
			}

			try {
				const res = await fetch(`${API_BASE}/participants/${squadId}/points`, {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
					body: JSON.stringify({ points: newScore })
				});

				if (res.ok) {
					showStatus('removePointsStatus', `✓ Punti rimossi. Nuovo punteggio: ${newScore}`, 'success');
					e.target.reset();
					window.location.reload();
				} else {
					showStatus('removePointsStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('removePointsStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function loadMatches() {
			const token = getAdminToken();
			if (!token) return;
			try {
				const res = await fetch(`${API_BASE}/market/admin/matches?limit=150`, {
					headers: { 'X-Admin-Token': token }
				});
				const matches = res.ok ? await res.json() : [];
				lastMatches = Array.isArray(matches) ? matches : [];
				const options = lastMatches.map(m => {
					const home = m.home_squad_name || m.home_squad_id;
					const away = m.away_squad_name || m.away_squad_id;
					return `<option value="${m.id}">#${m.id} ${home} ${m.home_score}-${m.away_score} ${away}</option>`;
				}).join('');
				const defaultOpt = '<option value="">Seleziona partita</option>';
				document.getElementById('editMatchSelect').innerHTML = defaultOpt + options;
				document.getElementById('deleteMatchSelect').innerHTML = defaultOpt + options;

				const editSel = document.getElementById('editMatchSelect');
				editSel.onchange = function() {
					const picked = lastMatches.find(m => Number(m.id) === Number(editSel.value));
					if (!picked) return;
					document.getElementById('editHomeScore').value = picked.home_score || 0;
					document.getElementById('editAwayScore').value = picked.away_score || 0;
					document.getElementById('editMatchSport').value = String(picked.sport || 'calcio').toLowerCase();
				};
			} catch (err) {
				console.error('Errore partite:', err);
			}
		}

		async function updateMatch(e) {
			e.preventDefault();
			const token = getAdminToken();
			if (!token) {
				showStatus('editMatchStatus', '✗ Admin token required', 'error');
				return;
			}
			const matchId = parseInt(document.getElementById('editMatchSelect').value);
			if (!matchId) {
				showStatus('editMatchStatus', '✗ Seleziona una partita', 'error');
				return;
			}
			try {
				const res = await fetch(`${API_BASE}/market/admin/matches/${matchId}`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
					body: JSON.stringify({
						home_score: parseInt(document.getElementById('editHomeScore').value || '0'),
						away_score: parseInt(document.getElementById('editAwayScore').value || '0'),
						sport: document.getElementById('editMatchSport').value,
					})
				});
				if (res.ok) {
					showStatus('editMatchStatus', '✓ Partita aggiornata', 'success');
					loadMatches();
				} else {
					showStatus('editMatchStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('editMatchStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function deleteMatch(e) {
			e.preventDefault();
			const token = getAdminToken();
			if (!token) {
				showStatus('deleteMatchStatus', '✗ Admin token required', 'error');
				return;
			}
			const matchId = parseInt(document.getElementById('deleteMatchSelect').value);
			if (!matchId) {
				showStatus('deleteMatchStatus', '✗ Seleziona una partita', 'error');
				return;
			}
			try {
				const res = await fetch(`${API_BASE}/market/admin/matches/${matchId}`, {
					method: 'DELETE',
					headers: { 'X-Admin-Token': token }
				});
				if (res.ok) {
					showStatus('deleteMatchStatus', '✓ Partita eliminata', 'success');
					loadMatches();
				} else {
					showStatus('deleteMatchStatus', '✗ ' + await readResponseMessage(res), 'error');
				}
			} catch (err) {
				showStatus('deleteMatchStatus', '✗ Errore: ' + err.message, 'error');
			}
		}

		async function loadSquads() {
			try {
				const res = await fetch(`${API_BASE}/participants`);
				const squads = await res.json();
				lastSquads = squads;

				const options = squads.map(s => `<option value="${s.id}">${s.name} (${s.role})</option>`).join('');
				const defaultOpt = '<option value="">Seleziona squadra</option>';
				document.getElementById('homeSquad').innerHTML = defaultOpt + options;
				document.getElementById('awaySquad').innerHTML = defaultOpt + options;
				document.getElementById('deleteSquadSelect').innerHTML = defaultOpt + options;
				document.getElementById('editSquadSelect').innerHTML = defaultOpt + options;

				const sel = document.getElementById('editSquadSelect');
				sel.onchange = function() {
					const picked = lastSquads.find(s => Number(s.id) === Number(sel.value));
					if (!picked) return;
					document.getElementById('editSquadName').value = picked.name || '';
					document.getElementById('editSquadSport').value = picked.role || 'Calcio';
					document.getElementById('editSquadCost').value = picked.cost || 0;
					document.getElementById('editSquadComposedOf').value = picked.composed_of || '';
				};
			} catch (err) {
				console.error('Errore caricamento squadre:', err);
			}
		}

		async function loadTeams() {
			try {
				const res = await fetch(`${API_BASE}/teams`);
				const teams = await res.json();
				console.log('Teams loaded:', teams);
			} catch (err) {
				console.error('Errore caricamento team:', err);
			}
		}

		document.addEventListener('DOMContentLoaded', initAdminToken);
		
		// Carica la vista di classifica iniziale
		setTimeout(() => loadRankingView(), 500);
	</script>
</body>
</html>
"""

	return HTMLResponse(content=html)
